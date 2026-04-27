SET NAMES utf8mb4;
SET time_zone = '+00:00';

CREATE TABLE IF NOT EXISTS users (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  username VARCHAR(64) NOT NULL UNIQUE,
  password_hash VARCHAR(120) NOT NULL,
  must_change_password TINYINT(1) NOT NULL DEFAULT 0,
  language VARCHAR(8) NOT NULL DEFAULT 'en',
  can_manage_users TINYINT(1) NOT NULL DEFAULT 0,
  can_manage_groups TINYINT(1) NOT NULL DEFAULT 0,
  can_manage_cameras TINYINT(1) NOT NULL DEFAULT 0,
  failed_login_count INT NOT NULL DEFAULT 0,
  failed_login_window_start DATETIME NULL,
  locked_until DATETIME NULL,
  last_login_at DATETIME NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS `groups` (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  parent_id BIGINT UNSIGNED NULL,
  name VARCHAR(128) NOT NULL,
  level TINYINT NOT NULL,
  sort_order INT NOT NULL DEFAULT 0,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_groups_parent (parent_id),
  CONSTRAINT fk_groups_parent FOREIGN KEY (parent_id) REFERENCES `groups`(id) ON DELETE CASCADE,
  CONSTRAINT chk_groups_level CHECK (level BETWEEN 1 AND 3)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS cameras (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  name VARCHAR(128) NOT NULL DEFAULT 'Camera',
  rtsp_url_enc VARBINARY(2048) NOT NULL,
  resolution_w INT NOT NULL DEFAULT 1920,
  resolution_h INT NOT NULL DEFAULT 1080,
  group_id BIGINT UNSIGNED NULL,
  display_enabled TINYINT(1) NOT NULL DEFAULT 1,
  dwell_limit_sec INT NOT NULL DEFAULT 180,
  count_limit INT NOT NULL DEFAULT 3,
  count_window_sec INT NOT NULL DEFAULT 86400,
  status VARCHAR(32) NOT NULL DEFAULT 'pending',
  last_status_at DATETIME NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uq_cameras_name_group (name, group_id),
  KEY idx_cameras_group (group_id),
  CONSTRAINT fk_cameras_group FOREIGN KEY (group_id) REFERENCES `groups`(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS camera_connection_log (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  camera_id BIGINT UNSIGNED NULL,
  attempt_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  success TINYINT(1) NOT NULL,
  error_code VARCHAR(64) NULL,
  error_detail TEXT NULL,
  PRIMARY KEY (id),
  KEY idx_ccl_camera (camera_id, attempt_at),
  CONSTRAINT fk_ccl_camera FOREIGN KEY (camera_id) REFERENCES cameras(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS user_visibility (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  user_id BIGINT UNSIGNED NOT NULL,
  group_id BIGINT UNSIGNED NULL,
  camera_id BIGINT UNSIGNED NULL,
  PRIMARY KEY (id),
  KEY idx_uv_user (user_id),
  CONSTRAINT fk_uv_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  CONSTRAINT fk_uv_group FOREIGN KEY (group_id) REFERENCES `groups`(id) ON DELETE CASCADE,
  CONSTRAINT fk_uv_camera FOREIGN KEY (camera_id) REFERENCES cameras(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS events (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  camera_id BIGINT UNSIGNED NOT NULL,
  group_path VARCHAR(255) NOT NULL DEFAULT '',
  person_global_id VARCHAR(64) NOT NULL,
  event_type ENUM('DWELL','REVISIT') NOT NULL,
  start_time DATETIME NOT NULL,
  end_time DATETIME NOT NULL,
  duration_sec INT NULL,
  appearance_count INT NULL,
  snapshot_path VARCHAR(255) NULL,
  clip_path VARCHAR(255) NULL,
  reviewed_by_user_id BIGINT UNSIGNED NULL,
  review_status ENUM('NEW','REVIEWED','FALSE_POSITIVE','ESCALATED') NOT NULL DEFAULT 'NEW',
  review_notes TEXT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_events_camera_time (camera_id, start_time),
  KEY idx_events_pgid (person_global_id),
  KEY idx_events_review (review_status),
  CONSTRAINT fk_events_camera FOREIGN KEY (camera_id) REFERENCES cameras(id) ON DELETE CASCADE,
  CONSTRAINT fk_events_reviewer FOREIGN KEY (reviewed_by_user_id) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS person_embeddings (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  store_group_id BIGINT UNSIGNED NULL,
  person_global_id VARCHAR(64) NOT NULL,
  embedding BLOB NOT NULL,
  last_seen_at DATETIME NOT NULL,
  PRIMARY KEY (id),
  KEY idx_pe_store_seen (store_group_id, last_seen_at),
  KEY idx_pe_pgid (person_global_id),
  CONSTRAINT fk_pe_group FOREIGN KEY (store_group_id) REFERENCES `groups`(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS audit_log (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  user_id BIGINT UNSIGNED NULL,
  action VARCHAR(64) NOT NULL,
  target_type VARCHAR(64) NULL,
  target_id VARCHAR(64) NULL,
  ip VARCHAR(64) NULL,
  detail JSON NULL,
  at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_audit_user_time (user_id, at),
  CONSTRAINT fk_audit_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS i18n_overrides (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  locale VARCHAR(8) NOT NULL,
  `key` VARCHAR(128) NOT NULL,
  value TEXT NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_i18n_locale_key (locale, `key`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
