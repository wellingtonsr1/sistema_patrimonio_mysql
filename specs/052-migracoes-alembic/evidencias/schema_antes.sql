
/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;
DROP TABLE IF EXISTS `ad_group_roles`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `ad_group_roles` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `group_name` varchar(255) NOT NULL,
  `role_id` int(11) NOT NULL,
  `priority` int(11) NOT NULL,
  `is_active` tinyint(1) NOT NULL,
  `created_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_ad_group_role_group` (`group_name`),
  UNIQUE KEY `ix_ad_group_roles_group_name` (`group_name`),
  KEY `ix_ad_group_roles_role_id` (`role_id`),
  KEY `ix_ad_group_roles_id` (`id`),
  CONSTRAINT `ad_group_roles_ibfk_1` FOREIGN KEY (`role_id`) REFERENCES `roles` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `ad_settings`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `ad_settings` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `enabled` tinyint(1) NOT NULL,
  `server` varchar(255) NOT NULL,
  `port` int(11) NOT NULL,
  `use_ldaps` tinyint(1) NOT NULL,
  `verify_tls` tinyint(1) NOT NULL,
  `base_dn` varchar(255) NOT NULL,
  `search_dn` varchar(255) DEFAULT NULL,
  `bind_user` varchar(255) DEFAULT NULL,
  `timeout_seconds` int(11) NOT NULL,
  `auto_create_user` tinyint(1) NOT NULL,
  `link_by_email` tinyint(1) NOT NULL,
  `group_role_priority` varchar(255) DEFAULT NULL,
  `disabled_behavior` varchar(20) NOT NULL,
  `updated_at` datetime DEFAULT NULL,
  `updated_by` varchar(100) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `assets`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `assets` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `tag` varchar(50) NOT NULL,
  `name` varchar(150) NOT NULL,
  `category` enum('NOTEBOOK','DESKTOP','MONITOR','SERVER','NETWORKING','PRINTER','SMARTPHONE','FURNITURE','VEHICLE','EQUIPMENT','OTHER') NOT NULL,
  `brand` varchar(100) DEFAULT NULL,
  `model` varchar(100) DEFAULT NULL,
  `serial_number` varchar(100) DEFAULT NULL,
  `specifications` text DEFAULT NULL,
  `purchase_date` datetime DEFAULT NULL,
  `purchase_value` float NOT NULL,
  `invoice_number` varchar(100) DEFAULT NULL,
  `supplier` varchar(150) DEFAULT NULL,
  `warranty_expiry` datetime DEFAULT NULL,
  `status` enum('AVAILABLE','IN_USE','IN_MAINTENANCE','IN_TRANSIT','WRITTEN_OFF') NOT NULL,
  `condition` enum('NEW','EXCELLENT','GOOD','FAIR','POOR','UNSERVICEABLE') NOT NULL,
  `location_id` int(11) DEFAULT NULL,
  `custodian_id` int(11) DEFAULT NULL,
  `notes` text DEFAULT NULL,
  `created_at` datetime DEFAULT NULL,
  `updated_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `ix_assets_tag` (`tag`),
  UNIQUE KEY `ix_assets_serial_number` (`serial_number`),
  KEY `location_id` (`location_id`),
  KEY `custodian_id` (`custodian_id`),
  KEY `ix_assets_name` (`name`),
  KEY `ix_assets_id` (`id`),
  CONSTRAINT `assets_ibfk_1` FOREIGN KEY (`location_id`) REFERENCES `locations` (`id`),
  CONSTRAINT `assets_ibfk_2` FOREIGN KEY (`custodian_id`) REFERENCES `custodians` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=46 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `audit_logs`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `audit_logs` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `timestamp` datetime NOT NULL,
  `user_id` int(11) DEFAULT NULL,
  `username` varchar(100) DEFAULT NULL,
  `action` varchar(50) NOT NULL,
  `module` varchar(50) DEFAULT NULL,
  `resource` varchar(100) DEFAULT NULL,
  `resource_id` int(11) DEFAULT NULL,
  `resource_ref` varchar(150) DEFAULT NULL,
  `ip_address` varchar(45) DEFAULT NULL,
  `result` varchar(20) NOT NULL,
  `description` text DEFAULT NULL,
  `previous_data` text DEFAULT NULL,
  `new_data` text DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `ix_audit_logs_id` (`id`),
  KEY `ix_audit_logs_timestamp` (`timestamp`),
  KEY `ix_audit_logs_module` (`module`),
  KEY `ix_audit_logs_user_id` (`user_id`),
  KEY `ix_audit_logs_action` (`action`),
  CONSTRAINT `audit_logs_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB AUTO_INCREMENT=104 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `backup_config`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `backup_config` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `auto_enabled` tinyint(1) NOT NULL,
  `schedule` varchar(10) DEFAULT NULL,
  `time` varchar(5) DEFAULT NULL,
  `weekday` int(11) DEFAULT NULL,
  `retention_daily_days` int(11) DEFAULT NULL,
  `retention_weekly_weeks` int(11) DEFAULT NULL,
  `retention_monthly_months` int(11) DEFAULT NULL,
  `keep_pre_restore` int(11) DEFAULT NULL,
  `updated_at` datetime DEFAULT NULL,
  `updated_by` varchar(100) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `backup_external_config`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `backup_external_config` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `enabled` tinyint(1) NOT NULL,
  `dest_type` varchar(20) NOT NULL,
  `dest_path` varchar(255) DEFAULT NULL,
  `updated_at` datetime DEFAULT NULL,
  `updated_by` varchar(100) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `backup_external_records`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `backup_external_records` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `filename` varchar(120) NOT NULL,
  `backup_type` varchar(20) NOT NULL,
  `status` varchar(10) NOT NULL,
  `copied_at` datetime NOT NULL,
  `size_bytes` int(11) DEFAULT NULL,
  `sha256` varchar(64) DEFAULT NULL,
  `error_description` varchar(255) DEFAULT NULL,
  `created_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `ix_backup_external_records_filename` (`filename`),
  KEY `ix_backup_external_records_id` (`id`),
  KEY `ix_backup_external_records_copied_at` (`copied_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `backup_records`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `backup_records` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `filename` varchar(120) NOT NULL,
  `backup_type` varchar(20) NOT NULL,
  `status` varchar(10) NOT NULL,
  `timestamp` datetime NOT NULL,
  `size_bytes` int(11) DEFAULT NULL,
  `sha256` varchar(64) DEFAULT NULL,
  `error_description` varchar(255) DEFAULT NULL,
  `removed_at` datetime DEFAULT NULL,
  `removed_reason` varchar(40) DEFAULT NULL,
  `created_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `ix_backup_records_filename` (`filename`),
  KEY `ix_backup_records_id` (`id`),
  KEY `ix_backup_records_timestamp` (`timestamp`),
  KEY `ix_backup_records_type_status` (`backup_type`,`status`)
) ENGINE=InnoDB AUTO_INCREMENT=15 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `custodians`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `custodians` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `registration_code` varchar(50) NOT NULL,
  `name` varchar(150) NOT NULL,
  `email` varchar(150) NOT NULL,
  `cpf` varchar(20) DEFAULT NULL,
  `role` varchar(100) NOT NULL,
  `department` varchar(100) NOT NULL,
  `is_active` tinyint(1) DEFAULT NULL,
  `created_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `ix_custodians_registration_code` (`registration_code`),
  UNIQUE KEY `ix_custodians_email` (`email`),
  KEY `ix_custodians_name` (`name`),
  KEY `ix_custodians_id` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=78 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `email_config`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `email_config` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `notifications_enabled` tinyint(1) NOT NULL,
  `recipients` text DEFAULT NULL,
  `updated_at` datetime DEFAULT NULL,
  `updated_by` varchar(100) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `integration_executions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `integration_executions` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `integration_key` varchar(30) NOT NULL,
  `operation` varchar(40) NOT NULL,
  `result` varchar(20) NOT NULL,
  `duration_ms` int(11) DEFAULT NULL,
  `user_id` int(11) DEFAULT NULL,
  `username` varchar(100) DEFAULT NULL,
  `movement_id` int(11) DEFAULT NULL,
  `detail` text DEFAULT NULL,
  `created_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `ix_integration_executions_key_created` (`integration_key`,`created_at`),
  KEY `ix_integration_executions_key_result_created` (`integration_key`,`result`,`created_at`),
  KEY `ix_integration_executions_user_id` (`user_id`),
  KEY `ix_integration_executions_created_at` (`created_at`),
  KEY `ix_integration_executions_integration_key` (`integration_key`),
  KEY `ix_integration_executions_result` (`result`),
  KEY `ix_integration_executions_id` (`id`),
  KEY `ix_integration_executions_movement_id` (`movement_id`),
  CONSTRAINT `integration_executions_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `inventario_itens`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `inventario_itens` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `inventario_id` int(11) NOT NULL,
  `asset_id` int(11) NOT NULL,
  `expected_location_id` int(11) DEFAULT NULL,
  `expected_location_name` varchar(150) DEFAULT NULL,
  `expected_custodian_name` varchar(150) DEFAULT NULL,
  `status` enum('PENDING','FOUND','FOUND_WRONG_LOCATION','NOT_FOUND','UNIDENTIFIED') NOT NULL,
  `nao_previsto` tinyint(1) NOT NULL,
  `found_location_id` int(11) DEFAULT NULL,
  `found_location_name` varchar(150) DEFAULT NULL,
  `observation` text DEFAULT NULL,
  `checked_by_id` int(11) DEFAULT NULL,
  `checked_by_name` varchar(100) DEFAULT NULL,
  `checked_at` datetime DEFAULT NULL,
  `created_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_inventario_item_asset` (`inventario_id`,`asset_id`),
  KEY `expected_location_id` (`expected_location_id`),
  KEY `found_location_id` (`found_location_id`),
  KEY `checked_by_id` (`checked_by_id`),
  KEY `ix_inventario_itens_asset_id` (`asset_id`),
  KEY `ix_inventario_itens_inventario_id` (`inventario_id`),
  KEY `ix_inventario_itens_status` (`status`),
  KEY `ix_inventario_itens_id` (`id`),
  CONSTRAINT `inventario_itens_ibfk_1` FOREIGN KEY (`inventario_id`) REFERENCES `inventarios` (`id`) ON DELETE CASCADE,
  CONSTRAINT `inventario_itens_ibfk_2` FOREIGN KEY (`asset_id`) REFERENCES `assets` (`id`) ON DELETE CASCADE,
  CONSTRAINT `inventario_itens_ibfk_3` FOREIGN KEY (`expected_location_id`) REFERENCES `locations` (`id`),
  CONSTRAINT `inventario_itens_ibfk_4` FOREIGN KEY (`found_location_id`) REFERENCES `locations` (`id`),
  CONSTRAINT `inventario_itens_ibfk_5` FOREIGN KEY (`checked_by_id`) REFERENCES `users` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB AUTO_INCREMENT=91 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `inventario_offline_coletas`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `inventario_offline_coletas` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `inventory_id` int(11) NOT NULL,
  `client_operation_id` varchar(64) NOT NULL,
  `status` enum('ACCEPTED','DUPLICATED','CONFLICT','REJECTED','RECONCILED') NOT NULL,
  `asset_id` int(11) NOT NULL,
  `inventario_item_id` int(11) DEFAULT NULL,
  `operation` varchar(20) NOT NULL,
  `result` varchar(30) DEFAULT NULL,
  `found_location_id` int(11) DEFAULT NULL,
  `found_custodian_id` int(11) DEFAULT NULL,
  `observation` text DEFAULT NULL,
  `device_id` varchar(64) NOT NULL,
  `user_id` int(11) DEFAULT NULL,
  `username` varchar(100) DEFAULT NULL,
  `collected_at` datetime NOT NULL,
  `received_at` datetime NOT NULL,
  `synced_at` datetime DEFAULT NULL,
  `reconciled_at` datetime DEFAULT NULL,
  `reconciled_by_id` int(11) DEFAULT NULL,
  `reconcile_action` varchar(20) DEFAULT NULL,
  `client_payload` text DEFAULT NULL,
  `reject_reason` varchar(255) DEFAULT NULL,
  `evidence_metadata` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL CHECK (json_valid(`evidence_metadata`)),
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_inventario_offline_coleta_operation` (`inventory_id`,`client_operation_id`),
  KEY `found_location_id` (`found_location_id`),
  KEY `found_custodian_id` (`found_custodian_id`),
  KEY `user_id` (`user_id`),
  KEY `reconciled_by_id` (`reconciled_by_id`),
  KEY `ix_inventario_offline_coletas_inventory_id` (`inventory_id`),
  KEY `ix_inventario_offline_coletas_id` (`id`),
  KEY `ix_inventario_offline_coletas_asset_id` (`asset_id`),
  KEY `ix_inventario_offline_coletas_inventario_item_id` (`inventario_item_id`),
  KEY `ix_inventario_offline_coletas_status` (`status`),
  KEY `ix_inventario_offline_coletas_client_operation_id` (`client_operation_id`),
  KEY `ix_inventario_offline_coletas_device_id` (`device_id`),
  KEY `ix_inv_off_coleta_inventory_status` (`inventory_id`,`status`),
  KEY `ix_inv_off_coleta_inventory_asset` (`inventory_id`,`asset_id`),
  CONSTRAINT `inventario_offline_coletas_ibfk_1` FOREIGN KEY (`inventory_id`) REFERENCES `inventarios` (`id`) ON DELETE CASCADE,
  CONSTRAINT `inventario_offline_coletas_ibfk_2` FOREIGN KEY (`asset_id`) REFERENCES `assets` (`id`),
  CONSTRAINT `inventario_offline_coletas_ibfk_3` FOREIGN KEY (`inventario_item_id`) REFERENCES `inventario_itens` (`id`),
  CONSTRAINT `inventario_offline_coletas_ibfk_4` FOREIGN KEY (`found_location_id`) REFERENCES `locations` (`id`),
  CONSTRAINT `inventario_offline_coletas_ibfk_5` FOREIGN KEY (`found_custodian_id`) REFERENCES `custodians` (`id`),
  CONSTRAINT `inventario_offline_coletas_ibfk_6` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE SET NULL,
  CONSTRAINT `inventario_offline_coletas_ibfk_7` FOREIGN KEY (`reconciled_by_id`) REFERENCES `users` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `inventarios`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `inventarios` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `code` varchar(50) NOT NULL,
  `name` varchar(150) NOT NULL,
  `status` enum('PLANNED','IN_PROGRESS','CLOSED') NOT NULL,
  `location_id` int(11) DEFAULT NULL,
  `department` varchar(100) DEFAULT NULL,
  `scope_filters` varchar(255) DEFAULT NULL,
  `notes` text DEFAULT NULL,
  `created_by_id` int(11) DEFAULT NULL,
  `created_by_name` varchar(100) DEFAULT NULL,
  `created_at` datetime DEFAULT NULL,
  `started_at` datetime DEFAULT NULL,
  `closed_at` datetime DEFAULT NULL,
  `closed_by_name` varchar(100) DEFAULT NULL,
  `closure_notes` text DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `ix_inventarios_code` (`code`),
  KEY `location_id` (`location_id`),
  KEY `created_by_id` (`created_by_id`),
  KEY `ix_inventarios_status` (`status`),
  KEY `ix_inventarios_id` (`id`),
  CONSTRAINT `inventarios_ibfk_1` FOREIGN KEY (`location_id`) REFERENCES `locations` (`id`),
  CONSTRAINT `inventarios_ibfk_2` FOREIGN KEY (`created_by_id`) REFERENCES `users` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `locations`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `locations` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(100) NOT NULL,
  `branch` varchar(100) NOT NULL,
  `building` varchar(100) DEFAULT NULL,
  `floor` varchar(50) DEFAULT NULL,
  `room` varchar(50) DEFAULT NULL,
  `department` varchar(100) NOT NULL,
  `manager_name` varchar(100) DEFAULT NULL,
  `description` text DEFAULT NULL,
  `created_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `ix_locations_name` (`name`),
  KEY `ix_locations_id` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=33 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `maintenances`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `maintenances` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `asset_id` int(11) NOT NULL,
  `maintenance_type` enum('PREVENTIVE','CORRECTIVE','UPGRADE') NOT NULL,
  `status` enum('SCHEDULED','IN_PROGRESS','COMPLETED','CANCELLED') NOT NULL,
  `provider_name` varchar(150) DEFAULT NULL,
  `description` text NOT NULL,
  `solution` text DEFAULT NULL,
  `cost` float DEFAULT NULL,
  `start_date` datetime NOT NULL,
  `end_date` datetime DEFAULT NULL,
  `created_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `ix_maintenances_id` (`id`),
  KEY `ix_maintenances_asset_id` (`asset_id`),
  CONSTRAINT `maintenances_ibfk_1` FOREIGN KEY (`asset_id`) REFERENCES `assets` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `movements`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `movements` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `movement_uuid` varchar(36) DEFAULT NULL,
  `asset_id` int(11) NOT NULL,
  `movement_type` enum('ACQUISITION','ALLOCATION','TRANSFER','MAINTENANCE_OUT','MAINTENANCE_IN','RETURN_STOCK','WRITE_OFF','STATUS_UPDATE') NOT NULL,
  `timestamp` datetime NOT NULL,
  `origin_location_id` int(11) DEFAULT NULL,
  `origin_location_name` varchar(150) DEFAULT NULL,
  `origin_custodian_id` int(11) DEFAULT NULL,
  `origin_custodian_name` varchar(150) DEFAULT NULL,
  `destination_location_id` int(11) DEFAULT NULL,
  `destination_location_name` varchar(150) DEFAULT NULL,
  `destination_custodian_id` int(11) DEFAULT NULL,
  `destination_custodian_name` varchar(150) DEFAULT NULL,
  `previous_status` enum('AVAILABLE','IN_USE','IN_MAINTENANCE','IN_TRANSIT','WRITTEN_OFF') DEFAULT NULL,
  `new_status` enum('AVAILABLE','IN_USE','IN_MAINTENANCE','IN_TRANSIT','WRITTEN_OFF') NOT NULL,
  `previous_condition` enum('NEW','EXCELLENT','GOOD','FAIR','POOR','UNSERVICEABLE') DEFAULT NULL,
  `new_condition` enum('NEW','EXCELLENT','GOOD','FAIR','POOR','UNSERVICEABLE') DEFAULT NULL,
  `reason` varchar(255) NOT NULL,
  `operator_name` varchar(100) NOT NULL,
  `term_code` varchar(50) DEFAULT NULL,
  `term_signed` tinyint(1) DEFAULT NULL,
  `notes` text DEFAULT NULL,
  `created_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `ix_movements_movement_uuid` (`movement_uuid`),
  KEY `origin_location_id` (`origin_location_id`),
  KEY `origin_custodian_id` (`origin_custodian_id`),
  KEY `destination_location_id` (`destination_location_id`),
  KEY `destination_custodian_id` (`destination_custodian_id`),
  KEY `ix_movements_asset_id` (`asset_id`),
  KEY `ix_movements_timestamp` (`timestamp`),
  KEY `ix_movements_movement_type` (`movement_type`),
  KEY `ix_movements_term_code` (`term_code`),
  KEY `ix_movements_id` (`id`),
  CONSTRAINT `movements_ibfk_1` FOREIGN KEY (`asset_id`) REFERENCES `assets` (`id`) ON DELETE CASCADE,
  CONSTRAINT `movements_ibfk_2` FOREIGN KEY (`origin_location_id`) REFERENCES `locations` (`id`),
  CONSTRAINT `movements_ibfk_3` FOREIGN KEY (`origin_custodian_id`) REFERENCES `custodians` (`id`),
  CONSTRAINT `movements_ibfk_4` FOREIGN KEY (`destination_location_id`) REFERENCES `locations` (`id`),
  CONSTRAINT `movements_ibfk_5` FOREIGN KEY (`destination_custodian_id`) REFERENCES `custodians` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=97 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `notifications`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `notifications` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `movement_id` int(11) NOT NULL,
  `status` varchar(20) NOT NULL,
  `recipients` text DEFAULT NULL,
  `subject` varchar(255) DEFAULT NULL,
  `attempt_count` int(11) NOT NULL,
  `last_attempt_at` datetime DEFAULT NULL,
  `sent_at` datetime DEFAULT NULL,
  `error_message` text DEFAULT NULL,
  `content_url` varchar(500) DEFAULT NULL,
  `created_at` datetime DEFAULT NULL,
  `updated_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_notifications_movement_id` (`movement_id`),
  UNIQUE KEY `movement_id` (`movement_id`),
  CONSTRAINT `notifications_ibfk_1` FOREIGN KEY (`movement_id`) REFERENCES `movements` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=7 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `onedoc_integrations`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `onedoc_integrations` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `movement_id` int(11) NOT NULL,
  `process_number` varchar(60) NOT NULL,
  `status` varchar(20) NOT NULL,
  `message_id` varchar(100) DEFAULT NULL,
  `attempt_count` int(11) NOT NULL,
  `last_attempt_at` datetime DEFAULT NULL,
  `sent_at` datetime DEFAULT NULL,
  `last_error_at` datetime DEFAULT NULL,
  `last_error` text DEFAULT NULL,
  `content_url` varchar(500) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_onedoc_integrations_movement_id` (`movement_id`),
  KEY `ix_onedoc_integrations_status` (`status`),
  KEY `ix_onedoc_integrations_movement_id` (`movement_id`),
  KEY `ix_onedoc_integrations_id` (`id`),
  CONSTRAINT `onedoc_integrations_ibfk_1` FOREIGN KEY (`movement_id`) REFERENCES `movements` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `permissions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `permissions` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(100) NOT NULL,
  `module` varchar(50) NOT NULL,
  `label` varchar(150) NOT NULL,
  `description` varchar(255) DEFAULT NULL,
  `created_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `ix_permissions_name` (`name`),
  KEY `ix_permissions_module` (`module`),
  KEY `ix_permissions_id` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=40 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `role_permissions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `role_permissions` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `role_id` int(11) NOT NULL,
  `permission_id` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_role_permission` (`role_id`,`permission_id`),
  KEY `ix_role_permissions_permission_id` (`permission_id`),
  KEY `ix_role_permissions_role_id` (`role_id`),
  KEY `ix_role_permissions_id` (`id`),
  CONSTRAINT `role_permissions_ibfk_1` FOREIGN KEY (`role_id`) REFERENCES `roles` (`id`) ON DELETE CASCADE,
  CONSTRAINT `role_permissions_ibfk_2` FOREIGN KEY (`permission_id`) REFERENCES `permissions` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=93 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `roles`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `roles` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(100) NOT NULL,
  `description` varchar(255) DEFAULT NULL,
  `is_system` tinyint(1) NOT NULL,
  `created_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `ix_roles_name` (`name`),
  KEY `ix_roles_id` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=8 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `setup_claims`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `setup_claims` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `claimed_at` datetime NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `user_roles`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `user_roles` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `user_id` int(11) NOT NULL,
  `role_id` int(11) NOT NULL,
  `assigned_by` varchar(20) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_user_role` (`user_id`,`role_id`),
  KEY `ix_user_roles_id` (`id`),
  KEY `ix_user_roles_role_id` (`role_id`),
  KEY `ix_user_roles_user_id` (`user_id`),
  CONSTRAINT `user_roles_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
  CONSTRAINT `user_roles_ibfk_2` FOREIGN KEY (`role_id`) REFERENCES `roles` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `user_sessions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `user_sessions` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `token_hash` varchar(64) NOT NULL,
  `user_id` int(11) NOT NULL,
  `created_at` datetime NOT NULL,
  `expires_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `ix_user_sessions_token_hash` (`token_hash`),
  KEY `ix_user_sessions_expires_at` (`expires_at`),
  KEY `ix_user_sessions_user_id` (`user_id`),
  KEY `ix_user_sessions_id` (`id`),
  CONSTRAINT `user_sessions_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=29 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `users`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `users` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `username` varchar(100) NOT NULL,
  `password_hash` varchar(255) NOT NULL,
  `full_name` varchar(150) DEFAULT NULL,
  `email` varchar(150) DEFAULT NULL,
  `is_active` tinyint(1) DEFAULT NULL,
  `is_admin` tinyint(1) DEFAULT NULL,
  `auth_provider` varchar(20) NOT NULL,
  `last_login` datetime DEFAULT NULL,
  `created_at` datetime DEFAULT NULL,
  `failed_login_attempts` int(11) NOT NULL,
  `locked_until` datetime DEFAULT NULL,
  `ad_object_guid` varchar(64) DEFAULT NULL,
  `ad_dn` varchar(400) DEFAULT NULL,
  `ad_last_sync` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `ix_users_username` (`username`),
  KEY `ix_users_id` (`id`),
  KEY `ix_users_ad_object_guid` (`ad_object_guid`)
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

