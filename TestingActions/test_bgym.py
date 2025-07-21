import gymnasium as gym
import browsergym.core  # register the openended task as a gym environment

import sys

# start an openended environment

env = gym.make(
    "browsergym/openended",
    task_kwargs={"start_url": "https://www.google.com/"},
    wait_for_user_message=True,
)

obs, info = env.reset() 
print("Env reset not done")

try:
    while True:
        print("Input request:")
        # Use sys.stdin.readline() instead of input() to avoid issues with input buffering
        print("Enter action: ", end="", flush=True)
        action = sys.stdin.readline()
        if not action:
            print("No input received, exiting.")
            break
        action = action.rstrip("\n")
        obs, reward, terminated, truncated, info = env.step(action)
        if terminated or truncated:
            break
finally:
    env.close()