"""
Queue adapter for Parsl
"""

import logging
import time
import traceback
from typing import Callable, Dict, List, Any, Optional

from .base_adapter import BaseAdapter


def _get_future(future):
    # if future.exception() is None: # This always seems to return None
    try:
        return future.result()
    except Exception as e:
        msg = "Caught Parsl Error:\n" + traceback.format_exc()
        ret = {"success": False, "error": msg}
        return ret


class ParslAdapter(BaseAdapter):
    """A Adapter for Parsl
    """

    def __init__(self, client: Any, logger: Optional[logging.Logger] = None, **kwargs):
        BaseAdapter.__init__(self, client, logger, **kwargs)

        import parsl
        self.client = parsl.dataflow.dflow.DataFlowKernel(self.client)
        self.app_map = {}
        import pdb; pdb.set_trace()
        pass

    def __repr__(self):
        return "<ParslAdapter client=<DataFlow label='{}'>>".format(self.client.config.executors[0].label)

    def get_app(self, function: str) -> Callable:
        """Obtains a Parsl python_application

        Parameters
        ----------
        function : str
            A full path to a function

        Returns
        -------
        callable
            The desired AppFactory

        Examples
        --------

        >>> get_app("numpy.einsum")
        <class PythonApp"AppFactory for einsum>
        """

        from parsl.app.app import python_app

        if function in self.app_map:
            return self.app_map[function]

        func = self.get_function(function)

        # TODO set walltime and the like
        self.app_map[function] = python_app(func, data_flow_kernel=self.client)

        return self.app_map[function]

    def submit_tasks(self, tasks: Dict[str, Any]) -> List[str]:
        ret = []
        for spec in tasks:

            tag = spec["id"]
            if tag in self.queue:
                continue

            # Form run tuple
            func = self.get_app(spec["spec"]["function"])
            # Trap QCEngine Memory and CPU
            if spec["spec"].startswith("qcengine.compute"):
                task_kwargs = spec["spec"]["kwargs"]

            task = func(*spec["spec"]["args"], **spec["spec"]["kwargs"])

            self.queue[tag] = (task, spec["parser"], spec["hooks"])
            self.logger.info("Adapter: Task submitted {}".format(tag))
            ret.append(tag)
        return ret

    def acquire_complete(self) -> List[Dict[str, Any]]:
        ret = {}
        del_keys = []
        for key, (future, parser, hooks) in self.queue.items():
            if future.done():
                ret[key] = (_get_future(future), parser, hooks)
                del_keys.append(key)

        for key in del_keys:
            del self.queue[key]

        return ret

    def await_results(self) -> bool:
        for future in self.queue.values():
            while future[0].done() is False:
                time.sleep(0.1)

        return True

    def close(self) -> bool:
        self.client.atexit_cleanup()
        return True
