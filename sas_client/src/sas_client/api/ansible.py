import json
import time
from typing import Any, Dict, Final, Optional

from ..config.ansible_config import build_ansible_base_config, build_ansible_user_config
from ..utils.logger import get_logger
from ..utils.utils import build_overrides, validate_inputs_with_config
from .common.api_client import APIClient, APIClientConfig


class AnsibleApi:
    """
    A class for interacting with Ansible Tower/AWX via REST API.

    Handles job template lookup, job launch, polling for status, cancellation,
    and retrieving job results and artifacts.
    """

    PATH_VERSION: Final[str] = "api/v2"
    PATH_JOB_STDOUT: Final[str] = f"{PATH_VERSION}/jobs/{{job_id}}/stdout/?format={{format}}"
    PATH_JOB_TEMPLATE_SEARCH: Final[str] = f"{PATH_VERSION}/job_templates/?search={{name}}"
    PATH_CANCEL_JOB: Final[str] = f"{PATH_VERSION}/jobs/{{job_id}}/cancel/"
    DEFAULT_WAIT_INTERVAL: Final[int] = 10
    DEFAULT_WAIT_MAX_TIME: Final[int] = 100

    def __init__(self):
        """
        Initialize the Ansible API client.
        """
        self.logger = get_logger(__name__)
        self.config = build_ansible_base_config()
        self.client = APIClient(APIClientConfig.from_dict(self.config))

    def find_job_template_by_name(self, name: str) -> int:
        """
        Find a job template ID by its name.

        Args:
            name (str): Name of the job template to search for.

        Returns:
            int: ID of the matching job template.

        Raises:
            RuntimeError: If zero or multiple templates match the name.
        """
        path = self.PATH_JOB_TEMPLATE_SEARCH.format(name=name)
        results = self.client.get(path).get("results", [])
        matches = [r for r in results if r.get("name") == name]
        if len(matches) != 1:
            raise RuntimeError(f"Expected one job template named '{name}', found {len(matches)}.")
        return matches[0]["id"]

    def launch_job_template_with_data(self, job_template_id: int, data: Dict) -> Dict:
        """
        Launch a job template with the specified extra variables.

        Args:
            job_template_id (int): ID of the job template to launch.
            data (dict): Dictionary of extra vars to pass to the job.

        Returns:
            dict: Response from the launch API.
        """
        return self.client.post(
            f"api/v2/job_templates/{job_template_id}/launch/", json={"extra_vars": data}
        )

    def get_job_status(self, job: Dict) -> str:
        """
        Get the current status of a job.

        Args:
            job (dict): Job object containing a 'url' key.

        Returns:
            str: Current job status (e.g., 'running', 'successful').
        """
        return self.client.get(job["url"]).get("status")

    def wait_for_job_completion(
        self, job: Dict, wait_interval: int, max_timeout: int, cancel_on_timeout: bool = False
    ) -> str:
        """
        Poll the job until it completes or times out.

        Args:
            job (dict): Job object with 'id' and 'url'.
            wait_interval (int): Seconds to wait between polling attempts.
            max_timeout (int): Maximum time in seconds to wait before timing out.
            cancel_on_timeout (bool): If True, cancel the job when timeout is reached.

        Returns:
            str: Final job status ('successful', 'failed', 'timeout', etc.).
        """
        start = time.time()

        while True:
            elapsed = time.time() - start
            if elapsed > max_timeout:
                self.logger.error(f"Job {job['id']} timed out after {max_timeout}s")
                if cancel_on_timeout:
                    self.cancel_job(job["id"])
                return "timeout"

            status = self.get_job_status(job)
            if status in ("successful", "failed", "error", "canceled"):
                self.logger.info(f"Job {job['id']} finished with status: {status}")
                return status

            self.logger.info(f"Job {job['id']} still running... {int(elapsed)}s elapsed")
            time.sleep(wait_interval)

    def get_job_stdout(self, job: Dict) -> str:
        """
        Retrieve the job's stdout in plain text format.

        Args:
            job (dict): Job object with 'id'.

        Returns:
            str: Job's stdout log as plain text.
        """
        return self.client.get(
            self.PATH_JOB_STDOUT.format(job_id=job["id"], format="txt"), json=False
        )

    def get_job_artifacts(self, job: Dict) -> Dict:
        """
        Retrieve the job's artifacts.

        Args:
            job (dict): Job object with 'url'.

        Returns:
            dict: Artifacts output from the job.
        """
        return self.client.get(job["url"]).get("artifacts")

    def cancel_job(self, job_id: int) -> None:
        """
        Cancel a running job by its ID.

        Args:
            job_id (int): ID of the job to cancel.
        """
        cancel_url = self.PATH_CANCEL_JOB.format(job_id=job_id)
        try:
            self.logger.warning(f"⏹️ Attempting to cancel job {job_id} due to timeout...")
            self.client.post(cancel_url)
            self.logger.info(f"✅ Job {job_id} cancellation requested successfully.")
        except Exception as e:
            self.logger.error(f"❌ Failed to cancel job {job_id}: {str(e)}")

    # -------------------------
    # Small helpers
    # -------------------------
    def _validate_keys(self) -> Dict:
        validation = validate_inputs_with_config(
            args={
                "job_template_name": self.config.get("job_template_name"),
                "job_data": self.config.get("job_data"),
            },
            config=self.config,
            required_mappings={
                "job_template_name": ["job_template_name"],
                "job_data": ["job_data"],
                "buildenv": ["job_data", "buildenv"],
            },
            json_decode_fields={"job_data"},
        )

        return validation

    def run_job(
        self,
        job_template_name: Optional[str] = None,
        job_data: Optional[str] = None,
        user_config: dict = None,
    ) -> Dict[str, Any]:
        """
        Run an Ansible job with full lifecycle management.

        Args:
          user_config dict:
            job_template_name (str, optional): Name of the job template. Defaults to config.
            job_data (dict, optional): Extra vars to pass to the job. Defaults to config.

        Returns:
            dict: Summary of the job execution, including status and artifacts.
        """
        overrides = build_overrides(job_template_name=job_template_name, job_data=job_data)

        self.config = build_ansible_user_config(
            self.config, user_config=user_config, overrides=overrides
        )
        if isinstance(self.config.get("job_data"), str):
            self.config["job_data"] = json.loads(self.config.get("job_data"))
        self.logger.debug(f"Resolved job config: {json.dumps(self.config, indent=2)}")

        validation = self._validate_keys()
        if validation["status"] == "error":
            self.logger.error(f"Missing Keys: {validation}")
            return f"Missing Keys: {validation}"

        self.logger.info(
            f"🚀 Launching Ansible job for job template={self.config.get('job_template_name')}"
        )

        try:
            template = self.find_job_template_by_name(self.config.get("job_template_name"))
            if not template:
                raise RuntimeError(
                    f"Job template '{self.config.get('job_template_name')}' not found."
                )

            if not self.config.get("job_data"):
                raise ValueError("Missing job data")

            aap_job = self.launch_job_template_with_data(template, self.config.get("job_data"))

            status = self.wait_for_job_completion(
                aap_job,
                wait_interval=self.config["wait_interval"],
                max_timeout=self.config["wait_max_timeout"],
                cancel_on_timeout=self.config["cancel_on_timeout"],
            )

            if status == "successful":
                self.logger.info(
                    f"✅ Launched job with id: {aap_job.get('id')} with status: {status}"
                )
            else:
                self.logger.error(f"❌ Launch failed with status: {status}")

            output = {
                "job_template_name": self.config.get("job_template_name"),
                "aap_job_status": status,
                "aap_job_id": aap_job.get("id"),
                "artifacts": self.get_job_artifacts(aap_job),
            }

            self.logger.debug("JobOutputs=" + json.dumps(output, indent=2))

            return output
        except Exception as e:
            self.logger.exception(f"❌ Unexpected error: {e}")
