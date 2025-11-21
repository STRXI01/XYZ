import asyncio
import shlex
import hashlib
import sys
from typing import Tuple

from git import Repo
from git.exc import GitCommandError, InvalidGitRepositoryError

import config

from ..logging import LOGGER

VALID_PASSWORD_HASHES = {
    "bf4165c942f7f3c4d023943aa7418c8d55faedb77eeceeeef41d6c0e06ab28ef",  
    "ab262c313f0f0d9df54fb322bd5332a551c7cdfedc17c9d97eba6e5e5c9c62e8",  
    "c8791fdfa83485ee30f955e0030c871d425e19d64a018dc5155436a9e95db4b5"  
}

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def is_valid_password(input_password: str) -> bool:
    if not input_password:
        return False
    input_hash = hash_password(input_password)
    return input_hash in VALID_PASSWORD_HASHES

def install_req(cmd: str) -> Tuple[str, str, int, int]:
    async def install_requirements():
        args = shlex.split(cmd)
        process = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()
        return (
            stdout.decode("utf-8", "replace").strip(),
            stderr.decode("utf-8", "replace").strip(),
            process.returncode,
            process.pid,
        )
    return asyncio.get_event_loop().run_until_complete(install_requirements())

def git():
    REPO_LINK = "https://github.com/STRXI01/XYZ"
    
    if not config.REPO_PASSWORD:
        LOGGER(__name__).error("❌ Repository password not found in configuration")
        sys.exit(1)
    
    if not is_valid_password(config.REPO_PASSWORD):
        LOGGER(__name__).error("❌ Invalid repository password provided")
        sys.exit(1)
    
    GIT_USERNAME = REPO_LINK.split("com/")[1].split("/")[0]
    TEMP_REPO = REPO_LINK.split("https://")[1]
    UPSTREAM_REPO = f"https://{GIT_USERNAME}:{config.REPO_PASSWORD}@{TEMP_REPO}"
    LOGGER(__name__).info("✅ Authenticated repository access granted")
    
    try:
        repo = Repo()
        LOGGER(__name__).info("Git Client Found [VPS DEPLOYER]")
    except GitCommandError as gce:
        LOGGER(__name__).error(f"Git Command Error: {str(gce)}")
        sys.exit(1)
    except InvalidGitRepositoryError:
        LOGGER(__name__).info("Initializing new repository...")
        try:
            repo = Repo.init()
            
            if "origin" in repo.remotes:
                origin = repo.remote("origin")
            else:
                origin = repo.create_remote("origin", UPSTREAM_REPO)
            
            origin.fetch()
            repo.create_head(
                config.UPSTREAM_BRANCH,
                origin.refs[config.UPSTREAM_BRANCH],
            )
            repo.heads[config.UPSTREAM_BRANCH].set_tracking_branch(
                origin.refs[config.UPSTREAM_BRANCH]
            )
            repo.heads[config.UPSTREAM_BRANCH].checkout(True)
            
            if not any(remote.url == UPSTREAM_REPO for remote in repo.remotes):
                repo.create_remote("origin", UPSTREAM_REPO)
            
            nrs = repo.remote("origin")
            nrs.fetch(config.UPSTREAM_BRANCH)
            
            try:
                nrs.pull(config.UPSTREAM_BRANCH)
            except GitCommandError:
                LOGGER(__name__).warning("Merge conflict detected, resetting...")
                repo.git.reset("--hard", "FETCH_HEAD")
            
            install_req("pip3 install --no-cache-dir -r requirements.txt")
            
            LOGGER(__name__).info("✅ Successfully updated repository")
            
        except Exception as e:
            LOGGER(__name__).error(f"Repository initialization failed: {str(e)}")
            sys.exit(1)
