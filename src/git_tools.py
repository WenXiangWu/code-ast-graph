"""
Git 工具模块 - 支持克隆仓库到 git-repos 目录
参照 code-index-demo 实现，简化鉴权配置
"""
import os
import re
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any, Callable, List
from urllib.parse import urlparse, urlunparse


class GitConfig:
    """Git 鉴权配置（从环境变量加载）"""
    
    def __init__(self):
        self.username = os.getenv('GIT_USERNAME')
        self.password = os.getenv('GIT_PASSWORD')
        self.token = os.getenv('GIT_TOKEN') or os.getenv('GIT_ACCESS_TOKEN')
        self.ssh_key_path = os.getenv('GIT_SSH_KEY_PATH')
        self.ssh_key_password = os.getenv('GIT_SSH_KEY_PASSWORD')
        self.auth_method = 'none'
        if self.ssh_key_path:
            self.auth_method = 'ssh'
        elif self.token:
            self.auth_method = 'token'
        elif self.username and self.password:
            self.auth_method = 'basic'
    
    def has_auth(self) -> bool:
        return self.auth_method != 'none'


class GitTool:
    """Git 操作工具"""
    
    def __init__(self, repos_base_dir: Optional[str] = None):
        if repos_base_dir:
            self.repos_base = Path(repos_base_dir).expanduser().resolve()
        else:
            project_root = Path(__file__).parent.parent
            self.repos_base = project_root / "git-repos"
        self.repos_base.mkdir(parents=True, exist_ok=True)
        self.config = GitConfig()
    
    def extract_repo_name(self, git_url: str) -> str:
        url = git_url.rstrip('/').rstrip('.git')
        parsed = urlparse(url)
        path = parsed.path.strip('/')
        if path:
            return path.split('/')[-1] if path else "repository"
        if '@' in url and ':' in url:
            path = url.split(':')[-1]
            return path.split('/')[-1] if path else "repository"
        return "repository"
    
    def _normalize_git_url(self, url: str) -> str:
        if not url:
            return ""
        url = url.strip()
        for prefix in ['https://', 'http://', 'git://', 'ssh://']:
            if url.startswith(prefix):
                url = url[len(prefix):]
                break
        if '@' in url:
            url = url.split('@', 1)[1]
        if url.endswith('.git'):
            url = url[:-4]
        return url.lower().rstrip('/')
    
    def _prepare_auth_url(self, git_url: str) -> str:
        if not self.config.has_auth():
            return git_url
        parsed = urlparse(git_url)
        if self.config.auth_method == 'token' and self.config.token:
            if '@' not in parsed.netloc:
                netloc = f"oauth2:{self.config.token}@{parsed.netloc}"
            else:
                netloc = f"oauth2:{self.config.token}@" + parsed.netloc.split('@')[-1]
            return urlunparse((parsed.scheme, netloc, parsed.path, parsed.params, parsed.query, parsed.fragment))
        elif self.config.auth_method == 'basic' and self.config.username and self.config.password:
            if '@' not in parsed.netloc:
                netloc = f"{self.config.username}:{self.config.password}@{parsed.netloc}"
            else:
                netloc = f"{self.config.username}:{self.config.password}@" + parsed.netloc.split('@')[-1]
            return urlunparse((parsed.scheme, netloc, parsed.path, parsed.params, parsed.query, parsed.fragment))
        return git_url
    
    def _prepare_auth_env(self) -> Dict[str, str]:
        env = os.environ.copy()
        if self.config.auth_method == 'ssh' and self.config.ssh_key_path:
            key_path = Path(self.config.ssh_key_path).expanduser().resolve()
            if key_path.exists():
                env['GIT_SSH_COMMAND'] = f'ssh -i "{key_path}" -o StrictHostKeyChecking=no'
        return env
    
    def clone_repository(
        self,
        git_url: str,
        branch: Optional[str] = None,
        progress_callback: Optional[Callable[[str], None]] = None
    ) -> Dict[str, Any]:
        """克隆 Git 仓库"""
        git_url = git_url.strip()
        if not git_url:
            return {'success': False, 'error': '请提供 Git URL'}
        
        branch = (branch or 'master').strip() or 'master'
        repo_name = self.extract_repo_name(git_url)
        local_path = self.repos_base / repo_name
        
        if local_path.exists() and (local_path / '.git').exists():
            try:
                result = subprocess.run(
                    ['git', 'remote', 'get-url', 'origin'],
                    cwd=str(local_path),
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.returncode == 0:
                    existing_url = result.stdout.strip()
                    if self._normalize_git_url(existing_url) == self._normalize_git_url(git_url):
                        return {
                            'success': False,
                            'error': '仓库已存在',
                            'local_path': str(local_path),
                            'repo_name': repo_name,
                            'already_exists': True
                        }
            except Exception:
                pass
        
        final_url = self._prepare_auth_url(git_url)
        env = self._prepare_auth_env()
        cmd = ['git', 'clone', '--branch', branch, '--single-branch', final_url, str(local_path)]
        
        if progress_callback:
            progress_callback(f"正在克隆: {git_url}")
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600, env=env)
            if result.returncode != 0:
                return {'success': False, 'error': result.stderr or result.stdout or '克隆失败'}
            if progress_callback:
                progress_callback(f"克隆成功: {repo_name}")
            return {'success': True, 'local_path': str(local_path), 'repo_name': repo_name, 'git_url': git_url}
        except subprocess.TimeoutExpired:
            return {'success': False, 'error': '克隆超时'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_repo_info(self, repo_path: str) -> Optional[Dict[str, Any]]:
        """获取仓库 Git 信息"""
        try:
            path = Path(repo_path)
            if not path.exists() or not (path / '.git').exists():
                return None
            result = subprocess.run(
                ['git', 'log', '-1', '--pretty=format:%H|%s|%an|%ai|%ar'],
                cwd=str(path),
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode != 0 or not result.stdout:
                return None
            parts = result.stdout.strip().split('|')
            if len(parts) >= 5:
                remote_result = subprocess.run(
                    ['git', 'remote', 'get-url', 'origin'],
                    cwd=str(path),
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                branch_result = subprocess.run(
                    ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
                    cwd=str(path),
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                return {
                    'commit_hash': parts[0],
                    'commit_message': parts[1],
                    'author': parts[2],
                    'commit_date': parts[3],
                    'commit_date_relative': parts[4],
                    'remote_url': remote_result.stdout.strip() if remote_result.returncode == 0 else None,
                    'branch': branch_result.stdout.strip() if branch_result.returncode == 0 else None
                }
        except Exception:
            pass
        return None
    
    def list_cloned_repos(self) -> List[Dict[str, Any]]:
        """列出 git-repos 下所有已克隆仓库"""
        repos = []
        if not self.repos_base.exists():
            return repos
        for item in self.repos_base.iterdir():
            if item.is_dir() and (item / '.git').exists():
                info = self.get_repo_info(str(item))
                repos.append({
                    'name': item.name,
                    'path': str(item),
                    'git_url': info.get('remote_url', '') if info else '',
                    'commit_hash': info.get('commit_hash', '') if info else '',
                    'commit_message': info.get('commit_message', '') if info else '',
                    'commit_author': info.get('author', '') if info else '',
                    'commit_date': info.get('commit_date', '') if info else '',
                    'commit_date_relative': info.get('commit_date_relative', '') if info else '',
                    'branch': info.get('branch', '') if info else '',
                })
        return repos
