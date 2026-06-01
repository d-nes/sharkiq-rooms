# Shark IQ Vacuum: Send to room component for Home Assistant
A custom component that allows Shark IQ Robot Vacuum to be sent to clean a specific room from Home Assistant.<br>
This project is entirely vibe-coded based on [sharkiq](https://github.com/sharkiqlibs/sharkiq) so treat it as such.

## Usage
- Place the files in your HA directory under *custom_components/sharkiq_custom*.
- Call from automation example:
```
action: vacuum.send_command
metadata: {}
data:
  command: clean_room
  params:
    room_name: Office
target:
  entity_id: vacuum.your_vacuum
```
