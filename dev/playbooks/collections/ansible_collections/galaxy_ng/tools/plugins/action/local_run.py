from ansible.plugins.action import ActionBase
import subprocess


class ActionModule(ActionBase):
    TRANSFERS_FILES = False
    _VALID_ARGS = frozenset(('command',))

    def run(self, tmp=None, task_vars=None):
        super(ActionModule, self).run(tmp, task_vars)

        # Retrieve the command from the task's arguments
        command = self._task.args.get('command', None)

        if command is None:
            return {"failed": True, "msg": "The 'command' argument is required"}

        try:
            # Run the command without capturing stdout or stderr
            subprocess.run(command, shell=True, check=True)
            return {"changed": True, "msg": "Command executed successfully"}
        except subprocess.CalledProcessError as e:
            return {"failed": True, "msg": "Command execution failed", "error": str(e)}
