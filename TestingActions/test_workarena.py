from agentlab.agents.generic_agent import AGENT_4o_MINI 

from agentlab.experiments.study import make_study
import os

# ServiceNow instance credentials come from the environment.
# Set SNOW_INSTANCE_PWD (and optionally URL/UNAME) before running this study.
os.environ.setdefault("SNOW_INSTANCE_URL", "https://dev283021.service-now.com")
os.environ.setdefault("SNOW_INSTANCE_UNAME", "admin")
if not os.environ.get("SNOW_INSTANCE_PWD"):
    raise RuntimeError("Set the SNOW_INSTANCE_PWD environment variable before running")


study = make_study(
    benchmark="workarena_l1",  # or "webarena", "workarena_l1" ...
    agent_args=[AGENT_4o_MINI],
    comment="My first study",
)

study.run(n_jobs=5)