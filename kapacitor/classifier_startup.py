# Copyright Intel Corporation

"""Kapacitor service
"""

import subprocess
import os
import os.path
import time
import tempfile
import sys
import json
import socket
import shlex
import logging
import shutil
from threading import Thread
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

TEMP_KAPACITOR_DIR = tempfile.gettempdir()
KAPACITOR_CERT = os.path.join(TEMP_KAPACITOR_DIR,
                              "kapacitor_server_certificate.pem")
KAPACITOR_KEY = os.path.join(TEMP_KAPACITOR_DIR, "kapacitor_server_key.pem")
KAPACITOR_CA = os.path.join(TEMP_KAPACITOR_DIR, "ca_certificate.pem")
KAPACITOR_CACERT = "/run/secrets/Kapacitor_Server/ca_certificate.pem"
KAPACITOR_SERVER_KEY = "/run/secrets/Kapacitor_Server/Kapacitor_Server_server_key.pem"
KAPACITOR_SERVER_CERT = "/run/secrets/Kapacitor_Server/Kapacitor_Server_server_certificate.pem"
KAPACITOR_DEV = "kapacitor_devmode.conf"
KAPACITOR_PROD = "kapacitor.conf"
SUCCESS = 0
FAILURE = -1
KAPACITOR_PORT = 9092
KAPACITOR_NAME = 'kapacitord'
CONFIG_KEY_PATH = 'config'
CONFIG_FILE = "/app/config.json"

logging.getLogger("watchdog.observers.inotify_buffer").setLevel(logging.WARNING)
class ConfigFileEventHandler(FileSystemEventHandler):
    def on_modified(self, event):
        if event.src_path.endswith("config.json"):
            logger.info(f"{event.src_path} file has been modified. Exiting to restart container...")
            os._exit(1)

class KapacitorClassifier():
    """Kapacitor Classifier have all the methods related to
       starting kapacitor, udf and tasks
    """
    def __init__(self, logger):
        self.logger = logger

    def write_cert(self, file_name, cert):
        """Write certificate to given file path
        """
        try:
            shutil.copy(cert, file_name)
            os.chmod(file_name, 0o400)
        except (OSError, IOError) as err:
            self.logger.debug("Failed creating file: {}, Error: {} ".format(
                file_name, err))

    def read_config(self, config, secure_mode, app_name):
        """Read the configuration from etcd
        """

        if secure_mode:
            self.write_cert(KAPACITOR_CERT, KAPACITOR_SERVER_CERT)
            self.write_cert(KAPACITOR_KEY, KAPACITOR_SERVER_KEY)
            self.write_cert(KAPACITOR_CA, KAPACITOR_CACERT)

    def install_udf_package(self):
        """ Install python package from udf/requirements.txt if exists
        """
        python_package_requirement_file = "/app/udfs/requirements.txt"
        python_package_installation_path = "/tmp/py_package"
        os.system(f"mkdir -p {python_package_installation_path}")
        if os.path.isfile(python_package_requirement_file):
            os.system(f"pip3 install -r {python_package_requirement_file} --target {python_package_installation_path}")

    def start_kapacitor(self,
                        config,
                        host_name,
                        secure_mode,
                        app_name):
        """Starts the kapacitor Daemon in the background
        """
        http_scheme = "http://"
        https_scheme = "https://"
        kapacitor_port = os.environ["KAPACITOR_URL"].split("://")[1]
        influxdb_hostname_port = os.environ[
            "KAPACITOR_INFLUXDB_0_URLS_0"].split("://")[1]

        try:
            if secure_mode:
                # Populate the certificates for kapacitor server
                kapacitor_conf = 'config/' + KAPACITOR_PROD

                os.environ["KAPACITOR_URL"] = "{}{}".format(https_scheme,
                                                            kapacitor_port)
                os.environ["KAPACITOR_UNSAFE_SSL"] = "false"
                os.environ["KAPACITOR_INFLUXDB_0_URLS_0"] = "{}{}".format(
                    https_scheme, influxdb_hostname_port)
            else:
                kapacitor_conf = 'config/' + KAPACITOR_DEV
                os.environ["KAPACITOR_URL"] = "{}{}".format(http_scheme,
                                                            kapacitor_port)
                os.environ["KAPACITOR_UNSAFE_SSL"] = "true"
                os.environ["KAPACITOR_INFLUXDB_0_URLS_0"] = "{}{}".format(
                    http_scheme, influxdb_hostname_port)

            self.read_config(config, secure_mode, app_name)
            subprocess.Popen(["kapacitord", "-hostname", host_name,
                              "-config", kapacitor_conf, "&"])
            self.logger.info("Started kapacitor Successfully...")
            return True
        except subprocess.CalledProcessError as err:
            self.logger.info("Exception Occured in Starting the Kapacitor " +
                             str(err))
            return False

    def process_zombie(self, process_name):
        """Checks the given process is Zombie State & returns True or False
        """
        try:
            out1 = subprocess.run(["ps", "-eaf"], stdout=subprocess.PIPE,
                                  check=False)
            out2 = subprocess.run(["grep", process_name], input=out1.stdout,
                                  stdout=subprocess.PIPE, check=False)
            out3 = subprocess.run(["grep", "-v", "grep"], input=out2.stdout,
                                  stdout=subprocess.PIPE, check=False)
            out4 = subprocess.run(["grep", "defunct"], input=out3.stdout,
                                  stdout=subprocess.PIPE, check=False)
            out = subprocess.run(["wc", "-l"], input=out4.stdout,
                                 stdout=subprocess.PIPE, check=False)
            out = out.stdout.decode('utf-8').rstrip("\n")

            if out == b'1':
                return True
            return False
        except subprocess.CalledProcessError as err:
            self.logger.info("Exception Occured in Starting Kapacitor " +
                             str(err))

    def kapacitor_port_open(self, host_name):
        """Verify Kapacitor's port is ready for accepting connection
        """
        if self.process_zombie(KAPACITOR_NAME):
            self.exit_with_failure_message("Kapacitor fail to start. "
                                           "Please verify the "
                                           "ia-kapacitor logs for "
                                           "UDF/kapacitor Errors.")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.logger.info("Attempting to connect to Kapacitor on port 9092")
        result = sock.connect_ex((host_name, KAPACITOR_PORT))
        self.logger.info("Attempted  Kapacitor on port 9092 : Result " +
                         str(result))
        if result == SUCCESS:
            self.logger.info("Successful in connecting to Kapacitor on"
                             "port 9092")
            return True

        return False

    def exit_with_failure_message(self, message):
        """Exit the container with failure message
        """
        if message:
            self.logger.error(message)
        sys.exit(FAILURE)

    def enable_classifier_task(self,
                               host_name,
                               tick_script,
                               task_name):
        """Enable the classifier TICK Script using the kapacitor CLI
        """
        retry_count = 5
        retry = 0
        kap_connectivity_retry = 50
        kap_retry = 0
        while not self.kapacitor_port_open(host_name):
            time.sleep(1)
            kap_retry = kap_retry + 1
            if kap_retry > kap_connectivity_retry:
                self.logger.error("Error connecting to Kapacitor Daemon... Restarting Kapacitor...")
                os._exit(1)

        self.logger.info("Kapacitor Port is Open for Communication....")
        while retry < retry_count:
            define_pointcl_cmd = ["kapacitor", "-skipVerify", "define",
                                  task_name, "-tick",
                                  "tick_scripts/" + tick_script]

            if subprocess.check_call(define_pointcl_cmd) == SUCCESS:
                define_pointcl_cmd = ["kapacitor", "-skipVerify", "enable",
                                      task_name]
                if subprocess.check_call(define_pointcl_cmd) == SUCCESS:
                    self.logger.info("Kapacitor Tasks Enabled Successfully")
                    self.logger.info("Kapacitor Initialized Successfully. "
                                     "Ready to Receive the Data....")
                    break

                self.logger.info("ERROR:Cannot Communicate to Kapacitor.")
            else:
                self.logger.info("ERROR:Cannot Communicate to Kapacitor. ")
            self.logger.info("Retrying Kapacitor Connection")
            time.sleep(0.0001)
            retry = retry + 1

    def check_config(self, config):
        """Starting the udf based on the config
           read from the etcd
        """
        # Checking if udf present in task and
        # run it based on etcd config
        if 'task' not in config.keys():
            error_msg = "task key is missing in config, EXITING!!!"
            return error_msg, FAILURE
        return None, SUCCESS

    def enable_tasks(self, config, kapacitor_started, host_name, secure_mode):
        """Starting the task based on the config
           read from the etcd
        """
        for task in config['task']:
            if 'tick_script' in task:
                tick_script = task['tick_script']
            else:
                error_msg = ("tick_script key is missing in config "
                             "Please provide the tick script to run "
                             "EXITING!!!!")
                return error_msg, FAILURE

            if 'task_name' in task:
                task_name = task['task_name']
            else:
                error_msg = ("task_name key is missing in config "
                             "Please provide the task name "
                             "EXITING!!!")
                return error_msg, FAILURE

            if kapacitor_started:
                self.logger.info("Enabling {0}".format(tick_script))
                self.enable_classifier_task(host_name,
                                            tick_script,
                                            task_name)

        if secure_mode:
            try:
                file_list = [KAPACITOR_CERT,
                             KAPACITOR_KEY]
                # Util.delete_certs(file_list)
            except (OSError, IOError):
                self.logger.error("Exception Occured while removing"
                                  "kapacitor certs")

        while True:
            time.sleep(10)


def config_file_watch(observer, CONFIG_FILE):
    logger.info(f"Monitoring {CONFIG_FILE} for config changes...")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

log_level = os.getenv('KAPACITOR_LOGGING_LEVEL', 'INFO').upper()
logging_level = getattr(logging, log_level, logging.INFO)

# Configure logging
logging.basicConfig(
    level=logging_level,  # Set the log level to DEBUG
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',  # Log format
)

logger = logging.getLogger(__name__)

def main():
    """Main to start kapacitor service
    """
    try:
        with open (CONFIG_FILE, 'r') as file:
            app_cfg = json.load(file)
        mode = os.getenv("SECURE_MODE", "true")
        secure_mode = mode.lower() == "true"

        config = app_cfg["config"]
        app_name = os.getenv("Appname", "Kapacitor")
    except Exception as e:
        logger.exception("Fetching app configuration failed, Error: {}".format(e))
        os._exit(1)

    event_handler = ConfigFileEventHandler()
    observer = Observer()
    observer.schedule(event_handler, path=CONFIG_FILE, recursive=False)
    observer.start()
    watch_config_change = Thread(target=config_file_watch, args=(observer,CONFIG_FILE,))
    watch_config_change.start()

    kapacitor_classifier = KapacitorClassifier(logger)

    logger.info("=============== STARTING kapacitor ==============")
    host_name = shlex.quote(os.environ["KAPACITOR_SERVER"])
    if not host_name:
        error_log = ('Kapacitor hostname is not Set in the container. '
                     'So exiting...')
        kapacitor_classifier.exit_with_failure_message(error_log)

    msg, status = kapacitor_classifier.check_config(config)
    if status is FAILURE:
        kapacitor_classifier.exit_with_failure_message(msg)
    kapacitor_classifier.install_udf_package()
    kapacitor_started = False
    if(kapacitor_classifier.start_kapacitor(config,
                                            host_name,
                                            secure_mode,
                                            app_name) is True):
        kapacitor_started = True
    else:
        error_log = "Kapacitor is not starting. So Exiting..."
        kapacitor_classifier.exit_with_failure_message(error_log)

    msg, status = kapacitor_classifier.enable_tasks(config,
                                                    kapacitor_started,
                                                    host_name,
                                                    secure_mode)
    if status is FAILURE:
        kapacitor_classifier.exit_with_failure_message(msg)


if __name__ == '__main__':
    main()
