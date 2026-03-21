-- =====================================================
-- Menu Migration: Chinese to English
-- Execute this script to update menu names from Chinese to English
-- =====================================================

-- Update parent menus
UPDATE menu_configs SET name = 'Dashboard' WHERE path = '/dashboard';
UPDATE menu_configs SET name = 'Instances' WHERE path = '/instances';
UPDATE menu_configs SET name = 'Environments' WHERE path = '/environments';
UPDATE menu_configs SET name = 'SQL Editor' WHERE path = '/sql-editor';
UPDATE menu_configs SET name = 'Approvals' WHERE path = '/approvals';
UPDATE menu_configs SET name = 'Monitor' WHERE path = '/monitor';
UPDATE menu_configs SET name = 'Scripts' WHERE path = '/scripts';
UPDATE menu_configs SET name = 'Scheduled Tasks' WHERE path = '/scheduled-tasks';
UPDATE menu_configs SET name = 'Users' WHERE path = '/users';
UPDATE menu_configs SET name = 'Registrations' WHERE path = '/registrations';
UPDATE menu_configs SET name = 'Notification' WHERE path = '/notification';
UPDATE menu_configs SET name = 'Audit Logs' WHERE path = '/audit';
UPDATE menu_configs SET name = 'Menu Config' WHERE path = '/menu-config';

-- Update child menus (Monitor sub-menus)
UPDATE menu_configs SET name = 'Performance' WHERE path = '/monitor/performance';
UPDATE menu_configs SET name = 'Slow Query' WHERE path = '/monitor/slow-query';
UPDATE menu_configs SET name = 'Monitor Settings' WHERE path = '/monitor/settings';

-- Verification query (run after migration)
-- SELECT id, name, path FROM menu_configs ORDER BY sort_order;
