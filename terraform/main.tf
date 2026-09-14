terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
    http = {
      source = "hashicorp/http"
    }
    azuread = {
      source  = "hashicorp/azuread"
      version = "~> 3.0"
    }
  }
  backend "azurerm" {
    resource_group_name  = "rg-journal-tfstate"
    storage_account_name = "stjournaltfstate8701"
    container_name       = "tfstate"
    key                  = "journal-api.tfstate"
  }
}

provider "azurerm" {
  features {}
  storage_use_azuread = true
}


resource "azurerm_resource_group" "main" {
  name     = "rg-${var.project}-${var.environment}"
  location = var.location

  tags = {
    project     = var.project
    environment = var.environment
    managed_by  = "terraform"
  }
}
resource "azurerm_user_assigned_identity" "app" {
  name                = "id-${var.project}-${var.environment}"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
}
resource "azurerm_storage_account" "journal" {
  name                     = "stjournaldev8701"
  resource_group_name      = azurerm_resource_group.main.name
  location                 = azurerm_resource_group.main.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  min_tls_version          = "TLS1_2"

  # Both account keys stop working. The app authenticates with its managed
  # identity instead, so there is no shared secret left to leak or rotate.
  shared_access_key_enabled = false

  tags = {
    environment = "dev"
    project     = "journal"
  }
}
data "http" "my_ip" {
  url = "https://ifconfig.me/ip"
}

resource "azurerm_postgresql_flexible_server" "main" {
  name                = "psql-${var.project}-${var.environment}-8701"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location

  version                = "16"
  administrator_login    = var.postgres_admin_username
  administrator_password = var.postgres_admin_password

  sku_name   = "B_Standard_B1ms"
  storage_mb = 32768
  zone       = "1"

  backup_retention_days        = 7
  geo_redundant_backup_enabled = false

  public_network_access_enabled = true

  tags = {
    project     = var.project
    environment = var.environment
    managed_by  = "terraform"
  }

}

resource "azurerm_postgresql_flexible_server_firewall_rule" "my_ip" {
  name             = "allow-my-ip"
  server_id        = azurerm_postgresql_flexible_server.main.id
  start_ip_address = chomp(data.http.my_ip.response_body)
  end_ip_address   = chomp(data.http.my_ip.response_body)
}

resource "azurerm_postgresql_flexible_server_database" "journal" {
  name      = "journaldb"
  server_id = azurerm_postgresql_flexible_server.main.id
  collation = "en_US.utf8"
  charset   = "utf8"
}
resource "azurerm_log_analytics_workspace" "main" {
  name                = "log-${var.project}-${var.environment}"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  sku                 = "PerGB2018"
  retention_in_days   = 30
}

resource "azurerm_container_app_environment" "main" {
  name                       = "cae-${var.project}-${var.environment}"
  resource_group_name        = azurerm_resource_group.main.name
  location                   = azurerm_resource_group.main.location
  log_analytics_workspace_id = azurerm_log_analytics_workspace.main.id
}
resource "azurerm_postgresql_flexible_server_firewall_rule" "azure_services" {
  name             = "allow-azure-services"
  server_id        = azurerm_postgresql_flexible_server.main.id
  start_ip_address = "0.0.0.0"
  end_ip_address   = "0.0.0.0"
}

resource "azurerm_container_app" "redis" {
  name                         = "redis"
  container_app_environment_id = azurerm_container_app_environment.main.id
  resource_group_name          = azurerm_resource_group.main.name
  revision_mode                = "Single"

  template {
    min_replicas = 1
    max_replicas = 1

    container {
      name   = "redis"
      image  = "redis:7"
      cpu    = 0.25
      memory = "0.5Gi"
    }
  }

  ingress {
    external_enabled = false
    target_port      = 6379
    exposed_port     = 6379
    transport        = "tcp"

    traffic_weight {
      latest_revision = true
      percentage      = 100
    }
  }
}
resource "azurerm_container_app" "api" {
  name                         = "journal-api"
  container_app_environment_id = azurerm_container_app_environment.main.id
  resource_group_name          = azurerm_resource_group.main.name
  revision_mode                = "Single"

  registry {
    server               = "ghcr.io"
    username             = var.github_username
    password_secret_name = "ghcr-token"
  }

  secret {
    name                = "ghcr-token"
    key_vault_secret_id = "${azurerm_key_vault.main.vault_uri}secrets/ghcr-token"
    identity            = azurerm_user_assigned_identity.app.id
  }

  secret {
    name                = "jwt-secret"
    key_vault_secret_id = "${azurerm_key_vault.main.vault_uri}secrets/jwt-secret"
    identity            = azurerm_user_assigned_identity.app.id
  }

  secret {
    name  = "database-url"
    value = "postgresql+asyncpg://${var.postgres_admin_username}:${urlencode(var.postgres_admin_password)}@${azurerm_postgresql_flexible_server.main.fqdn}:5432/journaldb?ssl=require"
  }

  template {
    min_replicas = 0
    max_replicas = 3

    http_scale_rule {
      name                = "http-scaling"
      concurrent_requests = 10
    }

    container {
      name   = "journal-api"
      image  = "ghcr.io/akadir695/journal-api:${var.image_tag}"
      cpu    = 0.5
      memory = "1Gi"

      env {
        name        = "DATABASE_URL"
        secret_name = "database-url"
      }

      env {
        name        = "JWT_SECRET"
        secret_name = "jwt-secret"
      }



      env {
        name  = "REDIS_URL"
        value = "redis://redis:6379/0"
      }

      env {
        name  = "ENVIRONMENT"
        value = "production"
      }

      env {
        name  = "AZURE_CLIENT_ID"
        value = azurerm_user_assigned_identity.app.client_id
      }
      env {
        name  = "APPLICATIONINSIGHTS_CONNECTION_STRING"
        value = azurerm_application_insights.main.connection_string
      }

      env {
        name  = "AZURE_STORAGE_ACCOUNT_NAME"
        value = azurerm_storage_account.journal.name
      }

      liveness_probe {
        transport = "HTTP"
        port      = 8000
        path      = "/health"
      }

      readiness_probe {
        transport = "HTTP"
        port      = 8000
        path      = "/health/ready"
      }
    }
  }

  ingress {
    external_enabled = true
    target_port      = 8000

    traffic_weight {
      latest_revision = true
      percentage      = 100
    }
  }
  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.app.id]
  }

  lifecycle {
    # CI owns the deployed image. Without this, terraform apply would revert
    # the container to image_tag and undo the most recent deploy.
    ignore_changes = [template[0].container[0].image]
  }
}
resource "azurerm_container_app" "worker" {
  name                         = "journal-worker"
  container_app_environment_id = azurerm_container_app_environment.main.id
  resource_group_name          = azurerm_resource_group.main.name
  revision_mode                = "Single"

  registry {
    server               = "ghcr.io"
    username             = var.github_username
    password_secret_name = "ghcr-token"
  }

  secret {
    name                = "ghcr-token"
    key_vault_secret_id = "${azurerm_key_vault.main.vault_uri}secrets/ghcr-token"
    identity            = azurerm_user_assigned_identity.app.id
  }

  secret {
    name                = "jwt-secret"
    key_vault_secret_id = "${azurerm_key_vault.main.vault_uri}secrets/jwt-secret"
    identity            = azurerm_user_assigned_identity.app.id
  }


  secret {
    name  = "database-url"
    value = "postgresql+asyncpg://${var.postgres_admin_username}:${urlencode(var.postgres_admin_password)}@${azurerm_postgresql_flexible_server.main.fqdn}:5432/journaldb?ssl=require"
  }

  secret {
    name                = "resend-api-key"
    key_vault_secret_id = "${azurerm_key_vault.main.vault_uri}secrets/resend-api-key"
    identity            = azurerm_user_assigned_identity.app.id
  }
  template {
    min_replicas = 1
    max_replicas = 1

    container {
      name    = "journal-worker"
      image   = "ghcr.io/akadir695/journal-api:${var.image_tag}"
      cpu     = 0.25
      memory  = "0.5Gi"
      command = ["arq", "app.workers.tasks.WorkerSettings"]

      env {
        name        = "DATABASE_URL"
        secret_name = "database-url"
      }

      env {
        name        = "JWT_SECRET"
        secret_name = "jwt-secret"
      }



      env {
        name        = "RESEND_API_KEY"
        secret_name = "resend-api-key"
      }

      env {
        name  = "REDIS_URL"
        value = "redis://redis:6379/0"
      }

      env {
        name  = "ENVIRONMENT"
        value = "production"
      }

      env {
        name  = "AZURE_CLIENT_ID"
        value = azurerm_user_assigned_identity.app.client_id
      }
      env {
        name  = "APPLICATIONINSIGHTS_CONNECTION_STRING"
        value = azurerm_application_insights.main.connection_string
      }

      env {
        name  = "AZURE_STORAGE_ACCOUNT_NAME"
        value = azurerm_storage_account.journal.name
      }
    }
  }
  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.app.id]
  }

  lifecycle {
    # CI owns the deployed image. Without this, terraform apply would revert
    # the container to image_tag and undo the most recent deploy.
    ignore_changes = [template[0].container[0].image]
  }
}

data "azurerm_client_config" "current" {}

resource "azurerm_key_vault" "main" {
  name                = "kv-${var.project}-${var.environment}-8701"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  tenant_id           = data.azurerm_client_config.current.tenant_id
  sku_name            = "standard"

  rbac_authorization_enabled = true
  purge_protection_enabled   = false
  soft_delete_retention_days = 7
}

resource "azurerm_role_assignment" "kv_app_read" {
  scope                = azurerm_key_vault.main.id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_user_assigned_identity.app.principal_id
}

resource "azurerm_role_assignment" "kv_me_write" {
  scope                = azurerm_key_vault.main.id
  role_definition_name = "Key Vault Secrets Officer"
  principal_id         = data.azurerm_client_config.current.object_id
}

resource "azurerm_role_assignment" "storage_blob" {
  scope                = azurerm_storage_account.journal.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azurerm_user_assigned_identity.app.principal_id
}

resource "azurerm_role_assignment" "storage_me" {
  scope                = azurerm_storage_account.journal.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = data.azurerm_client_config.current.object_id
}

resource "azurerm_role_assignment" "storage_delegator" {
  scope                = azurerm_storage_account.journal.id
  role_definition_name = "Storage Blob Delegator"
  principal_id         = azurerm_user_assigned_identity.app.principal_id
}

resource "azurerm_storage_container" "attachments" {
  name                  = var.azure_storage_container
  storage_account_id    = azurerm_storage_account.journal.id
  container_access_type = "private"
}
resource "azurerm_application_insights" "main" {
  name                = "appi-${var.project}-${var.environment}"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  workspace_id        = azurerm_log_analytics_workspace.main.id
  application_type    = "web"
}


# An identity for GitHub Actions. No password — it proves itself with a token.
resource "azuread_application" "ci" {
  display_name = "gh-${var.project}-${var.environment}"
}

resource "azuread_service_principal" "ci" {
  client_id = azuread_application.ci.client_id
}

# The trust rule. Azure accepts GitHub's token only when it claims to come
# from this exact repository on this exact branch.
resource "azuread_application_federated_identity_credential" "ci_main" {
  application_id = azuread_application.ci.id
  display_name   = "github-main"
  audiences      = ["api://AzureADTokenExchange"]
  issuer         = "https://token.actions.githubusercontent.com"
  # GitHub issues tokens with immutable numeric IDs for the owner and repo, so
  # the subject must match those rather than the display names. The IDs survive
  # a rename; the names do not.
  subject = "repo:Akadir695@126913888/journal-api@1315151603:ref:refs/heads/main"
}

# Scoped to the two container apps, not the resource group. The pipeline can
# deploy new images and nothing else — it cannot reach Postgres, Key Vault or
# storage even if the workflow is compromised.
resource "azurerm_role_assignment" "ci_api" {
  scope                = azurerm_container_app.api.id
  role_definition_name = "Contributor"
  principal_id         = azuread_service_principal.ci.object_id
}

resource "azurerm_role_assignment" "ci_worker" {
  scope                = azurerm_container_app.worker.id
  role_definition_name = "Contributor"
  principal_id         = azuread_service_principal.ci.object_id
}
# Found by the Day 45 rebuild: these were created in the portal and were not
# in Terraform, so they blocked the resource group deletion.
resource "azurerm_monitor_action_group" "email" {
  name                = "ag-journal-email"
  resource_group_name = azurerm_resource_group.main.name
  short_name          = "journal"

  email_receiver {
    name          = "email-me"
    email_address = var.alert_email
  }
}

resource "azurerm_monitor_scheduled_query_rules_alert_v2" "api_5xx" {
  name                = "journal-api-5xx"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location

  description = "Fires when the API returns any 5xx in a 5-minute window. 4xx are excluded: those mean the client sent something wrong, not that the server failed."
  severity    = 2

  scopes                  = [azurerm_application_insights.main.id]
  evaluation_frequency    = "PT5M"
  window_duration         = "PT5M"
  auto_mitigation_enabled = true

  criteria {
    query                   = <<-QUERY
      requests
      | where toint(resultCode) >= 500
    QUERY
    time_aggregation_method = "Count"
    threshold               = 0
    operator                = "GreaterThan"

    failing_periods {
      minimum_failing_periods_to_trigger_alert = 1
      number_of_evaluation_periods             = 1
    }
  }

  action {
    action_groups = [azurerm_monitor_action_group.email.id]
  }
}