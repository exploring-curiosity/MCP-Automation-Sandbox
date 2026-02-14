from blaxel.core import SyncSandboxInstance
import os
import time
import logging

logger = logging.getLogger(__name__)


class ScanResult:
    """Holds scan results and the live sandbox instance."""
    def __init__(self, results: dict, sandbox, sandbox_name: str):
        self.results = results
        self.sandbox = sandbox
        self.sandbox_name = sandbox_name

    def all_specs(self) -> list:
        """Return flat list of all extracted spec dicts."""
        specs = []
        for files in self.results.values():
            for f in files:
                if isinstance(f, dict):
                    specs.append(f)
        return specs

    def delete_sandbox(self):
        """Manually delete the sandbox when done."""
        if self.sandbox:
            logger.info(f"Deleting sandbox {self.sandbox_name}...")
            try:
                self.sandbox.delete()
                self.sandbox = None
            except Exception as e:
                logger.error(f"Failed to delete sandbox: {e}")


class Scanner:
    def __init__(self):
        pass

    def scan_all(self, repo_urls: list, progress_callback=None, extract_dir=None):
        """
        Scans multiple repositories for Swagger/OpenAPI documentation
        using a single shared sandbox.
        Returns a ScanResult containing results and the live sandbox.
        The sandbox is kept alive — caller is responsible for cleanup via
        scan_result.delete_sandbox() if/when desired.
        If extract_dir is provided, downloads file contents and saves them locally.
        Optional progress_callback(repo_url, index, total, message) is called for progress updates.
        """
        sandbox_name = f"scanner-{int(time.time())}"
        logger.info(f"Creating shared sandbox {sandbox_name} for {len(repo_urls)} repos")

        sandbox = None
        all_results = {}
        try:
            sandbox = SyncSandboxInstance.create(
                {
                    "name": sandbox_name,
                    "image": "blaxel/base-image:latest",
                    "region": "us-pdx-1"
                }
            )
            logger.info("Sandbox created")

            # Clone all repositories into the sandbox
            for i, repo_url in enumerate(repo_urls):
                repo_name = repo_url.split("/")[-1].replace(".git", "")
                logger.info(f"Cloning {repo_url} ({i+1}/{len(repo_urls)})...")

                exit_code, output = self._exec(sandbox, f"git clone {repo_url}")
                if exit_code != 0:
                    logger.error(f"Failed to clone {repo_url}: {output}")
                    all_results[repo_url] = []
                else:
                    logger.info(f"Cloned {repo_url}. Searching for Swagger files...")
                    find_cmd = (
                        f"find {repo_name} -iname 'swagger.json' -o -iname 'swagger.yaml' "
                        f"-o -iname 'openapi.json' -o -iname 'openapi.yaml'"
                    )
                    exit_code, output = self._exec(sandbox, find_cmd)

                    found_files = []
                    if exit_code == 0 and output:
                        lines = output.strip().split('\n')
                        found_files = [line.strip() for line in lines if line.strip()]

                    if extract_dir and found_files:
                        extracted = []
                        repo_out_dir = os.path.join(extract_dir, repo_name)
                        os.makedirs(repo_out_dir, exist_ok=True)
                        for fpath in found_files:
                            content = self._read_file(sandbox, fpath)
                            if content is not None:
                                local_name = os.path.basename(fpath)
                                local_path = os.path.join(repo_out_dir, local_name)
                                with open(local_path, 'w') as f:
                                    f.write(content)
                                extracted.append({
                                    'sandbox_path': fpath,
                                    'local_path': local_path,
                                    'content': content,
                                    'repo_name': repo_name,
                                })
                                logger.info(f"Extracted {fpath} -> {local_path}")
                        all_results[repo_url] = extracted
                    else:
                        all_results[repo_url] = found_files

                    logger.info(f"Found {len(found_files)} file(s) in {repo_url}")

                if progress_callback:
                    progress_callback(repo_url, i, len(repo_urls))

            return ScanResult(all_results, sandbox, sandbox_name)

        except Exception as e:
            logger.error(f"Error during scan: {e}")
            return ScanResult(all_results, sandbox, sandbox_name)

    def _read_file(self, sandbox, file_path):
        """
        Read the contents of a file from the sandbox.
        """
        exit_code, output = self._exec(sandbox, f"cat {file_path}")
        if exit_code == 0:
            # Strip any STDERR portion if present
            if "\nSTDERR:\n" in output:
                output = output.split("\nSTDERR:\n")[0]
            return output
        logger.error(f"Failed to read {file_path}: {output}")
        return None

    def _exec(self, sandbox, command_str):
        """
        Helper to execute command in sandbox and return (exit_code, output).
        """
        logger.debug(f"Executing: {command_str}")
        try:
            # Execute command
            result = sandbox.process.exec({"command": command_str})
            
            # Wait for completion
            wait_res = sandbox.process.wait(result.name)
            
            # Combine stdout and stderr for output
            output = ""
            if wait_res.stdout:
                output += wait_res.stdout
            if wait_res.stderr:
                output += "\nSTDERR:\n" + wait_res.stderr
                
            return wait_res.exit_code, output
        except Exception as e:
            logger.error(f"Failed to exec command: {e}")
            return -1, str(e)

