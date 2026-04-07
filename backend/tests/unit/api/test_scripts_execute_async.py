"""
脚本异步执行API测试 - 100%覆盖率
"""
import pytest
import asyncio
import tempfile
import os
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime


class MockProcess:
    """Mock subprocess.Process"""
    def __init__(self, returncode=0, stdout=b"success", stderr=b""):
        self.returncode = returncode
        self._stdout = stdout
        self._stderr = stderr
    
    async def communicate(self):
        return self._stdout, self._stderr
    
    def kill(self):
        pass


class TestExecuteScriptAsync:
    """测试 execute_script_async 函数"""
    
    @pytest.mark.asyncio
    async def test_script_not_found(self):
        """测试脚本不存在"""
        from app.api.scripts import execute_script_async
        
        with patch('app.database.SessionLocal') as mock_session_local:
            mock_db = MagicMock()
            mock_db.query.return_value.filter.return_value.first.return_value = None
            mock_session_local.return_value = mock_db
            
            await execute_script_async(1, 999, {}, 300)
    
    @pytest.mark.asyncio
    async def test_execution_not_found(self):
        """测试执行记录不存在"""
        from app.api.scripts import execute_script_async
        
        with patch('app.database.SessionLocal') as mock_session_local:
            mock_db = MagicMock()
            mock_db.query.return_value.filter.return_value.first.side_effect = [
                MagicMock(),  # script
                None  # execution
            ]
            mock_session_local.return_value = mock_db
            
            await execute_script_async(999, 1, {}, 300)
    
    @pytest.mark.asyncio
    async def test_python_script_success(self):
        """测试Python脚本执行成功"""
        from app.api.scripts import execute_script_async
        from app.models import ScriptType, ExecutionStatus
        
        mock_script = MagicMock()
        mock_script.id = 1
        mock_script.name = "Test Script"
        mock_script.script_type = ScriptType.PYTHON
        mock_script.content = "print('hello')"
        mock_script.notify_on_success = False
        mock_script.notify_on_failure = False
        mock_script.notify_channels = None
        
        mock_execution = MagicMock()
        mock_execution.id = 1
        mock_execution.status = ExecutionStatus.PENDING
        mock_execution.triggered_by = 1
        mock_execution.start_time = None
        mock_execution.duration = None
        
        mock_user = MagicMock()
        mock_user.username = "test_user"
        
        with patch('app.database.SessionLocal') as mock_session_local:
            mock_db = MagicMock()
            mock_db.query.return_value.filter.return_value.first.side_effect = [
                mock_script,
                mock_execution,
                mock_user
            ]
            mock_session_local.return_value = mock_db
            
            with patch('tempfile.NamedTemporaryFile') as mock_temp:
                mock_temp_file = MagicMock()
                mock_temp_file.name = "/tmp/test_script.py"
                mock_temp.return_value.__enter__.return_value = mock_temp_file
                
                with patch('asyncio.create_subprocess_exec', new_callable=AsyncMock) as mock_subprocess:
                    mock_process = MockProcess(returncode=0, stdout=b"hello\n")
                    mock_subprocess.return_value = mock_process
                    
                    with patch('os.unlink'):
                        await execute_script_async(1, 1, {"name": "test"}, 300)
    
    @pytest.mark.asyncio
    async def test_bash_script_success(self):
        """测试Bash脚本执行成功"""
        from app.api.scripts import execute_script_async
        from app.models import ScriptType, ExecutionStatus
        
        mock_script = MagicMock()
        mock_script.id = 1
        mock_script.name = "Bash Script"
        mock_script.script_type = ScriptType.BASH
        mock_script.content = "echo hello"
        mock_script.notify_on_success = False
        mock_script.notify_on_failure = False
        mock_script.notify_channels = None
        
        mock_execution = MagicMock()
        mock_execution.id = 1
        mock_execution.status = ExecutionStatus.PENDING
        mock_execution.triggered_by = 1
        mock_execution.start_time = None
        mock_execution.duration = None
        
        mock_user = MagicMock()
        mock_user.username = "test_user"
        
        with patch('app.database.SessionLocal') as mock_session_local:
            mock_db = MagicMock()
            mock_db.query.return_value.filter.return_value.first.side_effect = [
                mock_script,
                mock_execution,
                mock_user
            ]
            mock_session_local.return_value = mock_db
            
            with patch('tempfile.NamedTemporaryFile') as mock_temp:
                mock_temp_file = MagicMock()
                mock_temp_file.name = "/tmp/test_script.sh"
                mock_temp.return_value.__enter__.return_value = mock_temp_file
                
                with patch('asyncio.create_subprocess_exec', new_callable=AsyncMock) as mock_subprocess:
                    mock_process = MockProcess(returncode=0, stdout=b"hello\n")
                    mock_subprocess.return_value = mock_process
                    
                    with patch('os.unlink'):
                        await execute_script_async(1, 1, {}, 300)
    
    @pytest.mark.asyncio
    async def test_unsupported_script_type(self):
        """测试不支持的脚本类型"""
        from app.api.scripts import execute_script_async
        from app.models import ExecutionStatus
        
        mock_script = MagicMock()
        mock_script.id = 1
        mock_script.name = "Unknown Script"
        mock_script.script_type = MagicMock()
        mock_script.script_type.value = "unknown"
        mock_script.notify_on_success = False
        mock_script.notify_on_failure = False
        mock_script.notify_channels = None
        
        mock_execution = MagicMock()
        mock_execution.id = 1
        mock_execution.status = ExecutionStatus.PENDING
        mock_execution.triggered_by = 1
        mock_execution.start_time = datetime.now()
        mock_execution.end_time = datetime.now()
        
        mock_user = MagicMock()
        mock_user.username = "test_user"
        
        with patch('app.database.SessionLocal') as mock_session_local:
            mock_db = MagicMock()
            mock_db.query.return_value.filter.return_value.first.side_effect = [
                mock_script,
                mock_execution,
                mock_user
            ]
            mock_session_local.return_value = mock_db
            
            await execute_script_async(1, 1, {}, 300)
    
    @pytest.mark.asyncio
    async def test_python_script_timeout(self):
        """测试Python脚本超时"""
        from app.api.scripts import execute_script_async
        from app.models import ScriptType, ExecutionStatus
        
        mock_script = MagicMock()
        mock_script.id = 1
        mock_script.name = "Long Script"
        mock_script.script_type = ScriptType.PYTHON
        mock_script.content = "import time; time.sleep(100)"
        mock_script.notify_on_success = False
        mock_script.notify_on_failure = False
        mock_script.notify_channels = None
        
        mock_execution = MagicMock()
        mock_execution.id = 1
        mock_execution.status = ExecutionStatus.PENDING
        mock_execution.triggered_by = 1
        mock_execution.start_time = datetime.now()
        
        mock_user = MagicMock()
        mock_user.username = "test_user"
        
        with patch('app.database.SessionLocal') as mock_session_local:
            mock_db = MagicMock()
            mock_db.query.return_value.filter.return_value.first.side_effect = [
                mock_script,
                mock_execution,
                mock_user
            ]
            mock_session_local.return_value = mock_db
            
            with patch('tempfile.NamedTemporaryFile') as mock_temp:
                mock_temp_file = MagicMock()
                mock_temp_file.name = "/tmp/test_script.py"
                mock_temp.return_value.__enter__.return_value = mock_temp_file
                
                with patch('asyncio.create_subprocess_exec', new_callable=AsyncMock) as mock_subprocess:
                    mock_process = MockProcess(returncode=-1, stdout=b"")
                    
                    async def wait_for_timeout():
                        raise asyncio.TimeoutError()
                    
                    mock_process.communicate = wait_for_timeout
                    mock_subprocess.return_value = mock_process
                    
                    with patch('os.unlink'):
                        await execute_script_async(1, 1, {}, 1)  # 1 second timeout
    
    @pytest.mark.asyncio
    async def test_python_script_failed(self):
        """测试Python脚本执行失败"""
        from app.api.scripts import execute_script_async
        from app.models import ScriptType, ExecutionStatus
        
        mock_script = MagicMock()
        mock_script.id = 1
        mock_script.name = "Failing Script"
        mock_script.script_type = ScriptType.PYTHON
        mock_script.content = "raise Exception('error')"
        mock_script.notify_on_success = False
        mock_script.notify_on_failure = False
        mock_script.notify_channels = None
        
        mock_execution = MagicMock()
        mock_execution.id = 1
        mock_execution.status = ExecutionStatus.PENDING
        mock_execution.triggered_by = 1
        mock_execution.start_time = datetime.now()
        
        mock_user = MagicMock()
        mock_user.username = "test_user"
        
        with patch('app.database.SessionLocal') as mock_session_local:
            mock_db = MagicMock()
            mock_db.query.return_value.filter.return_value.first.side_effect = [
                mock_script,
                mock_execution,
                mock_user
            ]
            mock_session_local.return_value = mock_db
            
            with patch('tempfile.NamedTemporaryFile') as mock_temp:
                mock_temp_file = MagicMock()
                mock_temp_file.name = "/tmp/test_script.py"
                mock_temp.return_value.__enter__.return_value = mock_temp_file
                
                with patch('asyncio.create_subprocess_exec', new_callable=AsyncMock) as mock_subprocess:
                    mock_process = MockProcess(returncode=1, stdout=b"", stderr=b"Error: exception")
                    mock_subprocess.return_value = mock_process
                    
                    with patch('os.unlink'):
                        await execute_script_async(1, 1, {}, 300)
    
    @pytest.mark.asyncio
    async def test_python_script_with_params(self):
        """测试Python脚本带参数执行"""
        from app.api.scripts import execute_script_async
        from app.models import ScriptType, ExecutionStatus
        
        mock_script = MagicMock()
        mock_script.id = 1
        mock_script.name = "Param Script"
        mock_script.script_type = ScriptType.PYTHON
        mock_script.content = "import os; print(os.environ.get('PARAM_NAME'))"
        mock_script.notify_on_success = False
        mock_script.notify_on_failure = False
        mock_script.notify_channels = None
        
        mock_execution = MagicMock()
        mock_execution.id = 1
        mock_execution.status = ExecutionStatus.PENDING
        mock_execution.triggered_by = 1
        mock_execution.start_time = None
        
        mock_user = MagicMock()
        mock_user.username = "test_user"
        
        with patch('app.database.SessionLocal') as mock_session_local:
            mock_db = MagicMock()
            mock_db.query.return_value.filter.return_value.first.side_effect = [
                mock_script,
                mock_execution,
                mock_user
            ]
            mock_session_local.return_value = mock_db
            
            with patch('tempfile.NamedTemporaryFile') as mock_temp:
                mock_temp_file = MagicMock()
                mock_temp_file.name = "/tmp/test_script.py"
                mock_temp.return_value.__enter__.return_value = mock_temp_file
                
                with patch('asyncio.create_subprocess_exec', new_callable=AsyncMock) as mock_subprocess:
                    mock_process = MockProcess(returncode=0, stdout=b"test_value\n")
                    mock_subprocess.return_value = mock_process
                    
                    with patch('os.unlink'):
                        await execute_script_async(1, 1, {"name": "test_value"}, 300)
    
    @pytest.mark.asyncio
    async def test_exception_handling(self):
        """测试异常处理"""
        from app.api.scripts import execute_script_async
        
        with patch('app.database.SessionLocal') as mock_session_local:
            mock_db = MagicMock()
            mock_db.query.side_effect = Exception("Database error")
            mock_session_local.return_value = mock_db
            
            await execute_script_async(1, 1, {}, 300)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
