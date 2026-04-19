-- ============================================================
-- 运维管理平台 - MySQL 数据库初始化脚本
-- 支持 MySQL 5.7 / 8.0
-- ============================================================

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ----------------------------
-- 1. 用户表
-- ----------------------------
DROP TABLE IF EXISTS `users`;
CREATE TABLE `users` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `username` VARCHAR(50) NOT NULL,
  `password_hash` VARCHAR(255) NOT NULL,
  `real_name` VARCHAR(50),
  `email` VARCHAR(100),
  `phone` VARCHAR(20),
  `role` VARCHAR(20) NOT NULL,
  `status` TINYINT(1) NOT NULL DEFAULT 1,
  `failed_login_count` INT DEFAULT 0,
  `locked_until` DATETIME,
  `last_login_time` DATETIME,
  `last_login_ip` VARCHAR(50),
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_username` (`username`),
  UNIQUE KEY `uk_email` (`email`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT INTO `users` VALUES (1, 'admin', '$2b$12$oc/HyoBC/llyXzJFPuzGL.CwDuEWbEqcwc15idKSpMgZXKjf1vjLW', '超级管理员', 'admin@example.com', '18151519662', 'SUPER_ADMIN', True, 0, NULL, NULL, NULL, NOW(), NOW());
INSERT INTO `users` VALUES (2, 'zhangsan', '$2b$12$x8wBCzzfvW2GexZjOz5Nk.bbHW8C6NoHwkk4gUwQu9OZig88Xo9Uy', '张三', 'zhangsan@example.com', '13800138000', 'READONLY', True, 0, NULL, NULL, NULL, NOW(), NOW());
INSERT INTO `users` VALUES (3, 'test_operator2', '$2b$12$kKxZh3hiGDSKVawC4qsHDO0oUSmae15sNUiYFzha1v6Rk7KPuO08C', '测试运维2', 'test_operator2@example.com', '13800138002', 'OPERATOR', True, 0, NULL, NULL, NULL, NOW(), NOW());
INSERT INTO `users` VALUES (6, 'test_dev', '$2b$12$p.dKSF1w9mLTyYOOrERzku56tEh2NTUnkxzm6J1z3DWj2hytxw86K', '测试开发', 'dev@example.com', '', 'DEVELOPER', True, 0, NULL, NULL, NULL, NOW(), NOW());
INSERT INTO `users` VALUES (10, 'approver1', '$2b$12$PT.wj0g3ipdO.CIIuCiVvu42BK9TaJgIm7CFsYNNCgfYcZYPgoyJ2', '审批人1', 'approver1@example.com', '', 'APPROVAL_ADMIN', True, 0, NULL, NULL, NULL, NOW(), NOW());

-- ----------------------------
-- 2. 环境表
-- ----------------------------
DROP TABLE IF EXISTS `environments`;
CREATE TABLE `environments` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `name` VARCHAR(50) NOT NULL,
  `code` VARCHAR(20) NOT NULL,
  `color` VARCHAR(10) DEFAULT '#52C41A',
  `description` VARCHAR(200),
  `require_approval` TINYINT(1) DEFAULT 0,
  `status` TINYINT(1) DEFAULT 1,
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_code` (`code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT INTO `environments` VALUES (1, '开发环境', 'development', '#52C41A', '', False, True, NOW(), NOW());
INSERT INTO `environments` VALUES (2, '测试环境', 'testing', '#1890FF', '', False, True, NOW(), NOW());
INSERT INTO `environments` VALUES (4, '生产环境', 'production', '#FF4D4F', '', True, True, NOW(), NOW());

-- ----------------------------
-- 3. 权限表
-- ----------------------------
DROP TABLE IF EXISTS `permissions`;
CREATE TABLE `permissions` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `code` VARCHAR(100) NOT NULL,
  `name` VARCHAR(50) NOT NULL,
  `category` VARCHAR(20),
  `module` VARCHAR(50),
  `description` VARCHAR(200),
  `parent_id` INT,
  `sort_order` INT DEFAULT 0,
  `is_enabled` TINYINT(1) DEFAULT 1,
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_code` (`code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT INTO `permissions` VALUES (1, 'instance:view', '查看实例', 'menu', 'instance', '查看实例列表和详情', NULL, 100, True, NOW());
INSERT INTO `permissions` VALUES (2, 'instance:create', '创建实例', 'button', 'instance', '创建新实例', NULL, 101, True, NOW());
INSERT INTO `permissions` VALUES (3, 'instance:update', '编辑实例', 'button', 'instance', '编辑实例信息', NULL, 102, True, NOW());
INSERT INTO `permissions` VALUES (4, 'instance:delete', '删除实例', 'button', 'instance', '删除单个实例', NULL, 103, True, NOW());
INSERT INTO `permissions` VALUES (5, 'instance:test', '测试连接', 'button', 'instance', '测试实例连接', NULL, 104, True, NOW());
INSERT INTO `permissions` VALUES (6, 'instance:batch_delete', '批量删除', 'button', 'instance', '批量删除实例', NULL, 105, True, NOW());
INSERT INTO `permissions` VALUES (7, 'instance:batch_enable', '批量启用', 'button', 'instance', '批量启用实例', NULL, 106, True, NOW());
INSERT INTO `permissions` VALUES (8, 'instance:batch_disable', '批量禁用', 'button', 'instance', '批量禁用实例', NULL, 107, True, NOW());
INSERT INTO `permissions` VALUES (9, 'environment:view', '查看环境', 'menu', 'environment', '查看环境列表', NULL, 200, True, NOW());
INSERT INTO `permissions` VALUES (10, 'environment:create', '创建环境', 'button', 'environment', '创建新环境', NULL, 201, True, NOW());
INSERT INTO `permissions` VALUES (11, 'environment:update', '编辑环境', 'button', 'environment', '编辑环境信息', NULL, 202, True, NOW());
INSERT INTO `permissions` VALUES (12, 'environment:delete', '删除环境', 'button', 'environment', '删除环境', NULL, 203, True, NOW());
INSERT INTO `permissions` VALUES (13, 'environment:batch_delete', '批量删除环境', 'button', 'environment', '批量删除环境', NULL, 204, True, NOW());
INSERT INTO `permissions` VALUES (14, 'approval:view', '查看变更', 'menu', 'approval', '查看变更列表', NULL, 300, True, NOW());
INSERT INTO `permissions` VALUES (15, 'approval:create', '创建变更', 'button', 'approval', '创建变更申请', NULL, 301, True, NOW());
INSERT INTO `permissions` VALUES (16, 'approval:approve', '审批变更', 'button', 'approval', '审批变更请求', NULL, 302, True, NOW());
INSERT INTO `permissions` VALUES (17, 'approval:execute', '执行变更', 'button', 'approval', '执行SQL变更', NULL, 303, True, NOW());
INSERT INTO `permissions` VALUES (18, 'approval:revoke', '撤回变更', 'button', 'approval', '撤回变更申请', NULL, 304, True, NOW());
INSERT INTO `permissions` VALUES (19, 'approval:delete', '删除变更', 'button', 'approval', '删除变更记录', NULL, 305, True, NOW());
INSERT INTO `permissions` VALUES (20, 'approval:batch_approve', '批量审批', 'button', 'approval', '批量审批通过', NULL, 306, True, NOW());
INSERT INTO `permissions` VALUES (21, 'approval:batch_reject', '批量拒绝', 'button', 'approval', '批量审批拒绝', NULL, 307, True, NOW());
INSERT INTO `permissions` VALUES (22, 'approval:batch_delete', '批量删除', 'button', 'approval', '批量删除变更', NULL, 308, True, NOW());
INSERT INTO `permissions` VALUES (23, 'monitor:view', '查看监控', 'menu', 'monitor', '查看监控数据', NULL, 400, True, NOW());
INSERT INTO `permissions` VALUES (24, 'monitor:config', '配置监控', 'button', 'monitor', '配置监控参数', NULL, 401, True, NOW());
INSERT INTO `permissions` VALUES (25, 'script:view', '查看脚本', 'menu', 'script', '查看脚本列表', NULL, 600, True, NOW());
INSERT INTO `permissions` VALUES (26, 'script:create', '创建脚本', 'button', 'script', '创建新脚本', NULL, 601, True, NOW());
INSERT INTO `permissions` VALUES (27, 'script:execute', '执行脚本', 'button', 'script', '执行脚本', NULL, 602, True, NOW());
INSERT INTO `permissions` VALUES (28, 'script:delete', '删除脚本', 'button', 'script', '删除脚本', NULL, 603, True, NOW());
INSERT INTO `permissions` VALUES (29, 'system:user_manage', '用户管理', 'menu', 'system', '管理用户账号', NULL, 800, True, NOW());
INSERT INTO `permissions` VALUES (30, 'system:role_manage', '角色管理', 'button', 'system', '管理角色权限', NULL, 801, True, NOW());
INSERT INTO `permissions` VALUES (31, 'system:config', '系统配置', 'button', 'system', '修改系统配置', NULL, 802, True, NOW());
INSERT INTO `permissions` VALUES (32, 'system:audit_log', '审计日志', 'menu', 'system', '查看审计日志', NULL, 803, True, NOW());
INSERT INTO `permissions` VALUES (33, 'scheduler:view', '查看调度任务', 'button', 'scheduler', '查看调度任务列表和详情', NULL, 700, True, NOW());
INSERT INTO `permissions` VALUES (34, 'scheduler:manage', '管理调度任务', 'button', 'scheduler', '创建、编辑、删除调度任务', NULL, 701, True, NOW());
INSERT INTO `permissions` VALUES (35, 'notification:view', '查看通知管理', 'menu', 'notification', '访问通知管理菜单', NULL, 500, True, NOW());
INSERT INTO `permissions` VALUES (36, 'notification:channel_manage', '管理通知通道', 'button', 'notification', '创建、编辑、删除、测试通知通道', NULL, 501, True, NOW());
INSERT INTO `permissions` VALUES (37, 'notification:binding_manage', '管理通知绑定', 'button', 'notification', '配置通知通道与业务场景的绑定关系', NULL, 502, True, NOW());
INSERT INTO `permissions` VALUES (38, 'notification:template_manage', '管理通知模板', 'button', 'notification', '创建、编辑、删除通知模板', NULL, 503, True, NOW());
INSERT INTO `permissions` VALUES (39, 'notification:silence_manage', '管理静默规则', 'button', 'notification', '创建、编辑、删除通道静默规则', NULL, 504, True, NOW());
INSERT INTO `permissions` VALUES (48, 'key_rotation:view', '查看密钥轮换', 'menu', 'key_rotation', '', NULL, 900, True, NOW());
INSERT INTO `permissions` VALUES (49, 'key_rotation:config', '配置密钥轮换', 'button', 'key_rotation', '', NULL, 901, True, NOW());
INSERT INTO `permissions` VALUES (51, 'key_rotation:switch', '切换密钥版本', 'button', 'key_rotation', '', NULL, 903, True, NOW());
INSERT INTO `permissions` VALUES (52, 'key_rotation:migrate', '执行密钥迁移', 'button', 'key_rotation', '执行密钥数据迁移', NULL, 902, True, NOW());
INSERT INTO `permissions` VALUES (53, 'ai:model_view', '查看 AI 模型', 'menu', 'ai', '查看 AI 模型配置列表', NULL, 1000, True, NOW());
INSERT INTO `permissions` VALUES (54, 'ai:model_manage', '管理 AI 模型', 'button', 'ai', '创建、编辑、删除 AI 模型配置', NULL, 1001, True, NOW());

-- ----------------------------
-- 4. 角色权限关联表
-- ----------------------------
DROP TABLE IF EXISTS `role_permissions`;
CREATE TABLE `role_permissions` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `role` VARCHAR(20) NOT NULL,
  `permission_id` INT NOT NULL,
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_role_permission` (`role`, `permission_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT INTO `role_permissions` VALUES (67, 'developer', 1, NOW());
INSERT INTO `role_permissions` VALUES (68, 'developer', 5, NOW());
INSERT INTO `role_permissions` VALUES (69, 'developer', 9, NOW());
INSERT INTO `role_permissions` VALUES (70, 'developer', 14, NOW());
INSERT INTO `role_permissions` VALUES (71, 'developer', 15, NOW());
INSERT INTO `role_permissions` VALUES (72, 'developer', 18, NOW());
INSERT INTO `role_permissions` VALUES (73, 'developer', 23, NOW());
INSERT INTO `role_permissions` VALUES (74, 'developer', 25, NOW());
INSERT INTO `role_permissions` VALUES (206, 'developer', 33, NOW());
INSERT INTO `role_permissions` VALUES (411, 'super_admin', 1, NOW());
INSERT INTO `role_permissions` VALUES (412, 'super_admin', 33, NOW());
INSERT INTO `role_permissions` VALUES (413, 'super_admin', 2, NOW());
INSERT INTO `role_permissions` VALUES (414, 'super_admin', 34, NOW());
INSERT INTO `role_permissions` VALUES (415, 'super_admin', 3, NOW());
INSERT INTO `role_permissions` VALUES (416, 'super_admin', 4, NOW());
INSERT INTO `role_permissions` VALUES (417, 'super_admin', 5, NOW());
INSERT INTO `role_permissions` VALUES (418, 'super_admin', 6, NOW());
INSERT INTO `role_permissions` VALUES (419, 'super_admin', 7, NOW());
INSERT INTO `role_permissions` VALUES (420, 'super_admin', 8, NOW());
INSERT INTO `role_permissions` VALUES (421, 'super_admin', 9, NOW());
INSERT INTO `role_permissions` VALUES (422, 'super_admin', 10, NOW());
INSERT INTO `role_permissions` VALUES (423, 'super_admin', 11, NOW());
INSERT INTO `role_permissions` VALUES (424, 'super_admin', 12, NOW());
INSERT INTO `role_permissions` VALUES (425, 'super_admin', 13, NOW());
INSERT INTO `role_permissions` VALUES (426, 'super_admin', 14, NOW());
INSERT INTO `role_permissions` VALUES (427, 'super_admin', 15, NOW());
INSERT INTO `role_permissions` VALUES (428, 'super_admin', 16, NOW());
INSERT INTO `role_permissions` VALUES (429, 'super_admin', 17, NOW());
INSERT INTO `role_permissions` VALUES (430, 'super_admin', 18, NOW());
INSERT INTO `role_permissions` VALUES (431, 'super_admin', 19, NOW());
INSERT INTO `role_permissions` VALUES (432, 'super_admin', 20, NOW());
INSERT INTO `role_permissions` VALUES (433, 'super_admin', 21, NOW());
INSERT INTO `role_permissions` VALUES (434, 'super_admin', 22, NOW());
INSERT INTO `role_permissions` VALUES (435, 'super_admin', 23, NOW());
INSERT INTO `role_permissions` VALUES (436, 'super_admin', 24, NOW());
INSERT INTO `role_permissions` VALUES (437, 'super_admin', 25, NOW());
INSERT INTO `role_permissions` VALUES (438, 'super_admin', 26, NOW());
INSERT INTO `role_permissions` VALUES (439, 'super_admin', 27, NOW());
INSERT INTO `role_permissions` VALUES (440, 'super_admin', 28, NOW());
INSERT INTO `role_permissions` VALUES (441, 'super_admin', 29, NOW());
INSERT INTO `role_permissions` VALUES (442, 'super_admin', 30, NOW());
INSERT INTO `role_permissions` VALUES (443, 'super_admin', 31, NOW());
INSERT INTO `role_permissions` VALUES (444, 'super_admin', 32, NOW());
INSERT INTO `role_permissions` VALUES (445, 'super_admin', 35, NOW());
INSERT INTO `role_permissions` VALUES (446, 'super_admin', 37, NOW());
INSERT INTO `role_permissions` VALUES (447, 'super_admin', 36, NOW());
INSERT INTO `role_permissions` VALUES (449, 'super_admin', 39, NOW());
INSERT INTO `role_permissions` VALUES (450, 'super_admin', 38, NOW());
INSERT INTO `role_permissions` VALUES (457, 'developer', 35, NOW());
INSERT INTO `role_permissions` VALUES (461, 'developer', 36, NOW());
INSERT INTO `role_permissions` VALUES (463, 'developer', 38, NOW());
INSERT INTO `role_permissions` VALUES (471, 'developer', 39, NOW());
INSERT INTO `role_permissions` VALUES (473, 'developer', 37, NOW());
INSERT INTO `role_permissions` VALUES (476, 'super_admin', 48, NOW());
INSERT INTO `role_permissions` VALUES (477, 'super_admin', 49, NOW());
INSERT INTO `role_permissions` VALUES (479, 'super_admin', 51, NOW());
INSERT INTO `role_permissions` VALUES (800, 'super_admin', 53, NOW());
INSERT INTO `role_permissions` VALUES (801, 'super_admin', 54, NOW());
INSERT INTO `role_permissions` VALUES (503, 'readonly', 1, NOW());
INSERT INTO `role_permissions` VALUES (504, 'readonly', 33, NOW());
INSERT INTO `role_permissions` VALUES (505, 'readonly', 9, NOW());
INSERT INTO `role_permissions` VALUES (506, 'readonly', 14, NOW());
INSERT INTO `role_permissions` VALUES (507, 'readonly', 23, NOW());
INSERT INTO `role_permissions` VALUES (508, 'readonly', 25, NOW());
INSERT INTO `role_permissions` VALUES (509, 'readonly', 35, NOW());
INSERT INTO `role_permissions` VALUES (510, 'readonly', 36, NOW());
INSERT INTO `role_permissions` VALUES (511, 'readonly', 37, NOW());
INSERT INTO `role_permissions` VALUES (512, 'readonly', 38, NOW());
INSERT INTO `role_permissions` VALUES (513, 'readonly', 39, NOW());
INSERT INTO `role_permissions` VALUES (598, 'operator', 1, NOW());
INSERT INTO `role_permissions` VALUES (599, 'operator', 2, NOW());
INSERT INTO `role_permissions` VALUES (600, 'operator', 3, NOW());
INSERT INTO `role_permissions` VALUES (601, 'operator', 5, NOW());
INSERT INTO `role_permissions` VALUES (602, 'operator', 9, NOW());
INSERT INTO `role_permissions` VALUES (603, 'operator', 14, NOW());
INSERT INTO `role_permissions` VALUES (604, 'operator', 15, NOW());
INSERT INTO `role_permissions` VALUES (605, 'operator', 17, NOW());
INSERT INTO `role_permissions` VALUES (606, 'operator', 18, NOW());
INSERT INTO `role_permissions` VALUES (607, 'operator', 23, NOW());
INSERT INTO `role_permissions` VALUES (608, 'operator', 35, NOW());
INSERT INTO `role_permissions` VALUES (609, 'operator', 36, NOW());
INSERT INTO `role_permissions` VALUES (610, 'operator', 37, NOW());
INSERT INTO `role_permissions` VALUES (611, 'operator', 38, NOW());
INSERT INTO `role_permissions` VALUES (612, 'operator', 39, NOW());
INSERT INTO `role_permissions` VALUES (613, 'operator', 25, NOW());
INSERT INTO `role_permissions` VALUES (614, 'operator', 27, NOW());
INSERT INTO `role_permissions` VALUES (615, 'operator', 33, NOW());
INSERT INTO `role_permissions` VALUES (616, 'operator', 34, NOW());
INSERT INTO `role_permissions` VALUES (689, 'approval_admin', 1, NOW());
INSERT INTO `role_permissions` VALUES (690, 'approval_admin', 2, NOW());
INSERT INTO `role_permissions` VALUES (691, 'approval_admin', 3, NOW());
INSERT INTO `role_permissions` VALUES (692, 'approval_admin', 5, NOW());
INSERT INTO `role_permissions` VALUES (693, 'approval_admin', 9, NOW());
INSERT INTO `role_permissions` VALUES (694, 'approval_admin', 14, NOW());
INSERT INTO `role_permissions` VALUES (695, 'approval_admin', 15, NOW());
INSERT INTO `role_permissions` VALUES (696, 'approval_admin', 16, NOW());
INSERT INTO `role_permissions` VALUES (697, 'approval_admin', 17, NOW());
INSERT INTO `role_permissions` VALUES (698, 'approval_admin', 18, NOW());
INSERT INTO `role_permissions` VALUES (699, 'approval_admin', 19, NOW());
INSERT INTO `role_permissions` VALUES (700, 'approval_admin', 20, NOW());
INSERT INTO `role_permissions` VALUES (701, 'approval_admin', 21, NOW());
INSERT INTO `role_permissions` VALUES (702, 'approval_admin', 22, NOW());
INSERT INTO `role_permissions` VALUES (703, 'approval_admin', 23, NOW());
INSERT INTO `role_permissions` VALUES (704, 'approval_admin', 24, NOW());
INSERT INTO `role_permissions` VALUES (705, 'approval_admin', 35, NOW());
INSERT INTO `role_permissions` VALUES (706, 'approval_admin', 36, NOW());
INSERT INTO `role_permissions` VALUES (707, 'approval_admin', 37, NOW());
INSERT INTO `role_permissions` VALUES (708, 'approval_admin', 38, NOW());
INSERT INTO `role_permissions` VALUES (709, 'approval_admin', 39, NOW());
INSERT INTO `role_permissions` VALUES (710, 'approval_admin', 25, NOW());
INSERT INTO `role_permissions` VALUES (711, 'approval_admin', 26, NOW());
INSERT INTO `role_permissions` VALUES (712, 'approval_admin', 27, NOW());
INSERT INTO `role_permissions` VALUES (713, 'approval_admin', 28, NOW());
INSERT INTO `role_permissions` VALUES (714, 'approval_admin', 33, NOW());
INSERT INTO `role_permissions` VALUES (715, 'approval_admin', 34, NOW());
INSERT INTO `role_permissions` VALUES (716, 'approval_admin', 32, NOW());

-- ----------------------------
-- 5. 角色环境关联表
-- ----------------------------
DROP TABLE IF EXISTS `role_environments`;
CREATE TABLE `role_environments` (
      `id` INT NOT NULL AUTO_INCREMENT,
      `role` VARCHAR(20) NOT NULL,
      `environment_id` INT NOT NULL,
      PRIMARY KEY (`id`),
      UNIQUE KEY `uk_role_env` (`role`, `environment_id`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT INTO `role_environments` VALUES (12, 'developer', 1);
INSERT INTO `role_environments` VALUES (13, 'developer', 2);
INSERT INTO `role_environments` VALUES (43, 'super_admin', 2);
INSERT INTO `role_environments` VALUES (44, 'super_admin', 4);
INSERT INTO `role_environments` VALUES (45, 'super_admin', 1);
INSERT INTO `role_environments` VALUES (48, 'approval_admin', 2);
INSERT INTO `role_environments` VALUES (49, 'approval_admin', 4);
INSERT INTO `role_environments` VALUES (50, 'approval_admin', 1);
INSERT INTO `role_environments` VALUES (55, 'operator', 1);
INSERT INTO `role_environments` VALUES (56, 'operator', 2);
INSERT INTO `role_environments` VALUES (57, 'readonly', 2);
INSERT INTO `role_environments` VALUES (58, 'readonly', 1);

-- ----------------------------
-- 6. 菜单配置表
-- ----------------------------
DROP TABLE IF EXISTS `menu_configs`;
CREATE TABLE `menu_configs` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `name` VARCHAR(50) NOT NULL,
  `path` VARCHAR(200) NOT NULL,
  `icon` VARCHAR(50),
  `permission` VARCHAR(100),
  `parent_id` INT,
  `sort_order` INT DEFAULT 0,
  `is_enabled` TINYINT(1) DEFAULT 1,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT INTO `menu_configs` VALUES (1, '仪表盘', '/dashboard', 'DataAnalysis', '', NULL, 1, True);
INSERT INTO `menu_configs` VALUES (2, '资源管理', 'None', 'Coin', '', NULL, 10, True);
INSERT INTO `menu_configs` VALUES (3, 'SQL工具', 'None', 'Document', '', NULL, 20, True);
INSERT INTO `menu_configs` VALUES (4, '变更管理', '/change', 'Stamp', '', NULL, 30, True);
INSERT INTO `menu_configs` VALUES (5, '监控中心', '/monitor', 'Monitor', '', NULL, 40, True);
INSERT INTO `menu_configs` VALUES (6, '自动化', 'None', 'Promotion', '', NULL, 50, True);
INSERT INTO `menu_configs` VALUES (7, '系统管理', 'None', 'Setting', '', NULL, 100, True);
INSERT INTO `menu_configs` VALUES (19, 'Redis变更', '/change/redis-requests', 'Key', '', 4, 2, True);
INSERT INTO `menu_configs` VALUES (21, '实例管理', '/instances', 'Grid', 'instance:view', 2, 11, True);
INSERT INTO `menu_configs` VALUES (22, '环境管理', '/environments', 'Collection', 'environment:view', 2, 12, True);
INSERT INTO `menu_configs` VALUES (31, 'SQL编辑器', '/sql-editor', 'Edit', '', 3, 21, True);
INSERT INTO `menu_configs` VALUES (32, 'SQL优化器', '/sql-optimizer', 'MagicStick', '', 3, 22, True);
INSERT INTO `menu_configs` VALUES (41, 'DB变更', '/change/requests', 'Coin', 'approval:view', 4, 1, True);
INSERT INTO `menu_configs` VALUES (51, '性能监控', '/monitor/performance', 'TrendCharts', 'monitor:view', 5, 1, True);
INSERT INTO `menu_configs` VALUES (52, '慢查询监控', '/monitor/slow-query', 'Timer', 'monitor:view', 5, 2, True);
INSERT INTO `menu_configs` VALUES (53, '监控配置', '/monitor/settings', 'Setting', 'monitor:config', 5, 9, True);
INSERT INTO `menu_configs` VALUES (61, '脚本管理', '/scripts', 'DocumentCopy', 'script:view', 6, 51, True);
INSERT INTO `menu_configs` VALUES (62, '定时任务', '/scheduled-tasks', 'AlarmClock', 'scheduler:view', 6, 52, True);
INSERT INTO `menu_configs` VALUES (71, '用户管理', '/users', 'User', 'system:user_manage', 7, 101, True);
INSERT INTO `menu_configs` VALUES (73, '菜单配置', '/menu-config', 'Menu', 'system:role_manage', 7, 102, True);
INSERT INTO `menu_configs` VALUES (75, '审计日志', '/audit', 'Tickets', 'system:audit_log', 7, 103, True);
INSERT INTO `menu_configs` VALUES (76, '系统设置', '/system', 'Tools', 'system:config', 7, 104, True);
INSERT INTO `menu_configs` VALUES (77, '权限管理', '/permissions', 'Lock', 'system:role_manage', 7, 105, True);
INSERT INTO `menu_configs` VALUES (83, '变更窗口', '/change/windows', 'Clock', '', 4, 3, True);
INSERT INTO `menu_configs` VALUES (85, '告警中心', '/monitor/alerts', 'Bell', 'monitor:view', 5, 3, True);
INSERT INTO `menu_configs` VALUES (86, '主从复制', '/monitor/replication', 'Connection', 'monitor:view', 5, 4, True);
INSERT INTO `menu_configs` VALUES (87, '事务与锁', '/monitor/locks', 'Lock', 'monitor:view', 5, 5, True);
INSERT INTO `menu_configs` VALUES (88, '巡检报告', '/monitor/inspection', 'DocumentChecked', 'monitor:view', 5, 6, True);
INSERT INTO `menu_configs` VALUES (89, '定时巡检', '/monitor/scheduled-inspection', 'AlarmClock', 'monitor:view', 5, 7, True);
INSERT INTO `menu_configs` VALUES (91, '通知管理', '/notification', 'Bell', 'notification:view', NULL, 60, True);
INSERT INTO `menu_configs` VALUES (93, '通道管理', '/notification/channels', 'Connection', '', 91, 62, True);
INSERT INTO `menu_configs` VALUES (94, '通知历史', '/notification/logs', 'List', '', 91, 63, True);
INSERT INTO `menu_configs` VALUES (95, '通知模板', '/notification/templates', 'Document', '', 91, 64, True);
INSERT INTO `menu_configs` VALUES (96, 'AI 模型配置', '/ai-models', 'MagicStick', 'ai:model_view', 7, 15, True);
INSERT INTO `menu_configs` VALUES (97, 'SQL性能对比', '/monitor/sql-performance', 'DataLine', '', 5, 90, True);

-- ----------------------------
-- 7-71. 其他业务表
-- 说明：以下表由 SQLAlchemy 模型自动创建，
--       运行 `python -c "from app.models import *; from app.database import engine, Base; Base.metadata.create_all(bind=engine)"`
-- ----------------------------
-- rdb_instances
-- redis_instances
-- instance_groups
-- scripts
-- scheduled_tasks
-- script_executions
-- approval_flows
-- approval_records
-- audit_logs
-- login_logs
-- notification_channels
-- notification_templates
-- notification_bindings
-- alert_rules
-- alert_records
-- alert_silence_rules
-- monitor_switches
-- key_rotation_config
-- key_rotation_keys
-- key_rotation_logs
-- jwt_rotation_config
-- jwt_rotation_keys
-- ai_model_configs
-- ai_scene_configs
-- ai_available_models
-- ai_call_logs
-- system_configs
-- global_configs

SET FOREIGN_KEY_CHECKS = 1;
