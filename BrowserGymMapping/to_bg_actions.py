## Jude's code.



import os
import pandas as pd
from datetime import datetime
import json
from pymongo import MongoClient
from collections import defaultdict

# Connect to MongoDB using the connection string from the environment.
# Set ATLAS_URI, e.g. mongodb+srv://<username>:<password>@<cluster-host>/
connection_string = os.environ.get("ATLAS_URI")
if not connection_string:
    raise RuntimeError("ATLAS_URI environment variable is not set")
client = MongoClient(connection_string)

# Access the database and collection
db = client["webcapstone"]
events_collection = db["events"]

# Get example event
def get_one_trajectory():
    events = events_collection.find_one()
    return events

def get_all_trajectories():
    return list(events_collection.find())

def group_events_by_bid(events):
    """Group events by their BID (Browser ID)"""
    bid_groups = []
    current_bid = None
    current_group = []
    
    for event in events:
        # Extract BID from target if available
        bid = None

        if 'target' in event and 'bid' in event['target']:
            bid = event['target']['bid']
        
        if bid is None: 
            continue
        
        if bid == current_bid:
            current_group.append(event)
        else:
            bid_groups.append(current_group)
            current_group = [event]
            current_bid = bid
    
    if len(current_group) > 0:
        bid_groups.append(current_group)
    
    return bid_groups[1:]

def action_start(event_group, target_event_type):
    """find first event of target type
    """
    i = 0
    while i < len(event_group):
        if event_group[i]['type'] == target_event_type:
            return i
        i += 1
    return -1

def action_sequence(event_group, initial_event_id, additional_event_types):
    """ find all actions before and after initial event that match additional event types
    """
    group_start, group_end = 0, len(event_group)

    i = initial_event_id
    while i >=0:
        if event_group[i]['type'] not in additional_event_types:
            group_start = i+1
            break
        i -= 1
    
    i = initial_event_id
    while i < len(event_group):
        if event_group[i]['type'] not in additional_event_types:
            group_end = i
            break
        i += 1
    
    return group_start, group_end

def find_inputs(event_groups):
    def input_seq(event_group, start):
        i = start 
        group_start, group_end = 0, len(event_group)
        input_value = None
        
        while i >= 0:
            if event_group[i]['type'] not in ['keydown', 'keyup', 'keypress']:
                group_start = i+1
                break
            i -= 1
        i = start
        
        while i < len(event_group):
            if event_group[i]['type'] not in ['keydown', 'keyup', 'keypress', 'input']:
                group_end = i
                break
            if event_group[i]['type'] == 'input':
                input_value = event_group[i]['target']['value']
            i += 1
        
        return group_start, group_end, input_value
        
    new_groups = []
    input_actions = []
    
    for i, event_group in enumerate(event_groups):
        start = action_start(event_group, 'input')
        
        if start == -1:
            # do nothing
            new_groups.append(event_group)
            continue
        
        group_start, group_end, input_value = input_seq(event_group, start)
        if group_start > 0:
            new_groups.append(event_group[:group_start])
        if group_end < len(event_group):
            new_groups.append(event_group[group_end:])
        input_actions.append(('fill', event_group[group_end-1]['target']['bid'], event_group[group_end-1]['timestamp'], input_value))
    
    return input_actions, new_groups

def find_clicks(event_groups):
    new_groups = []
    click_actions = []
    
    for i, event_group in enumerate(event_groups):
        click_event_id = action_start(event_group, 'click')
        
        if click_event_id == -1:
            # do nothing
            new_groups.append(event_group)
            continue
        
        group_start, group_end = action_sequence(event_group, click_event_id, ['mousedown', 'mouseup', 'mouseover', 'mouseout', 'focus', 'blur'])
        
        if group_start > 0:
            new_groups.append(event_group[:group_start])
        if group_end < len(event_group):
            new_groups.append(event_group[group_end:])
        
        click_actions.append(('click', event_group[click_event_id]['target']['bid'], event_group[click_event_id]['timestamp']))

    return click_actions, new_groups

def find_select(event_groups):
    new_groups = []
    actions = []
    
    for i, event_group in enumerate(event_groups):
        event_id = action_start(event_group, 'change')
        
        if event_id == -1:
            new_groups.append(event_group)
            continue
    
        value = event_group[event_id]['target']['value']

        group_start, group_end = action_sequence(event_group, event_id, ['input'])
        
        if group_start > 0:
            new_groups.append(event_group[:group_start])
        if group_end < len(event_group):
            new_groups.append(event_group[group_end:])
        
        actions.append(('select_option', event_group[event_id]['target']['bid'], event_group[event_id]['timestamp'], value))

    return actions, new_groups

def order_actions(actions, *more_actions):
    for action in more_actions:
        actions += action
    actions.sort(key=lambda x: x[1])
    return actions

if __name__ == "__main__":
    # Get all events
    trajectories = get_all_trajectories()
    # for i, trajectory in enumerate(trajectories):
    #     for j, event in enumerate(trajectory['events']):
    #         if event['type'] == 'input':
    #             print(i, j, 'a', event['target']['text'], 'b',  event['target']['value'])

    for i, events in enumerate(trajectories):
        groups = group_events_by_bid(events['events'])
        select_actions, new_groups = find_select(groups)
        input_actions, new_groups = find_inputs(new_groups)
        # print(i, input_actions, [len(g) for g in groups], [len(g) for g in new_groups])
        click_actions, new_groups = find_clicks(new_groups)
        actions = order_actions(select_actions, input_actions, click_actions)
        print(i, actions)