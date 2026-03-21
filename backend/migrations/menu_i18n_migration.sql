-- =====================================================
-- Menu Migration: English to Chinese
-- Execute this script to update menu names from English to Chinese
-- =====================================================

-- Update parent menus
UPDATE menu_configs SET name = '仪表盘' WHERE path = '/dashboard';
UPDATE menu_configs SET name = '实例管理' WHERE path = '/instances';
UPDATE menu_configs SET name = '环境管理' WHERE path = '/environments';
UPDATE menu_configs SET name = 'SQL编辑器' WHERE path = '/sql-editor';
UPDATE menu_configs SET name = '变更审批' WHERE path = '/approvals';
UPDATE menu_configs SET name = '监控中心' WHERE path = '/monitor';
UPDATE menu_configs SET name = '脚本管理' WHERE path = '/scripts';
UPDATE menu_configs SET name = '定时任务' WHERE path = '/scheduled-tasks';
UPDATE menu_configs SET name = '用户管理' WHERE path = '/users';
UPDATE menu_configs SET name = '注册审批' WHERE path = '/registrations';
UPDATE menu_configs SET name = '通知管理' WHERE path = '/notification';
UPDATE menu_configs SET name = '审计日志' WHERE path = '/audit';
UPDATE menu_configs SET name = '菜单配置' WHERE path = '/menu-config';

-- Update child menus (Monitor sub-menus)
UPDATE menu_configs SET name = '性能监控' WHERE path = '/monitor/performance';
UPDATE menu_configs SET name = '慢查询监控' WHERE path = '/monitor/slow-query';
UPDATE menu_configs SET name = '监控配置' WHERE path = '/monitor/settings';

-- Verification query (run after migration)
-- SELECT id, name, path FROM menu_configs ORDER BY sort_order;
