## Description

rig prototype that can mutate over time in real-time, while fully preserving it's animation.

## Instructions
- open `mutable_rig.ma` in a maya session.
- run `mutable_rig.py` in the script editor to make the required code available to the included *scriptNode*.
- scrub through the timeline to load/switch rigs. There's a rig change at frame 10.

## Technical considerations

There are plenty of ways to implement this in a pipeline; kept this proof of concept intentionally simple.

Set up in maya for familiarity, but a real-time engine would probably do better.

Maya crashes easily unless we defer the script's evaluation, which compromises updates during playback and introduces a lag where updates only happen after a 2nd time change.

Reading *animCurve* keyframes directly solves the issue, but it isn't guaranteed to exist.
Using a *scriptJob* or *callback* listening to value changes didn't make it any better but would also be needed to account for user interaction over the current frame.
