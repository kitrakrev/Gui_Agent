from agentlab.agents.generic_agent import AGENT_4o_MINI 

from agentlab.experiments.study import make_study
import os

os.environ["SNOW_INSTANCE_URL"] = "https://dev283021.service-now.com"
os.environ["SNOW_INSTANCE_UNAME"] = "admin"
os.environ["SNOW_INSTANCE_PWD"] = "FXug1M/gi/8F"


study = make_study(
    benchmark="workarena_l1",  # or "webarena", "workarena_l1" ...
    agent_args=[AGENT_4o_MINI],
    comment="My first study",
)

study.run(n_jobs=5)