import pyautogui as p
import time

time.sleep(2)

# Open Spotlight and search for Spotify
p.hotkey('command', 'space')
time.sleep(1)  # Wait for Spotlight to open
p.write("spotify")
time.sleep(1)  # Wait for the search to complete
p.press('enter')
time.sleep(5)  # Wait for Spotify to open

# Locate the search bar in Spotify and click it
# Replace 'search.png' with the correct path to your screenshot
res = p.locateCenterOnScreen("search.png", confidence=0.8)
if res is not None:
    p.click(res)
else:
    print("Search bar not found.")
    exit()

# Search for the song
time.sleep(2)  # Wait for the search bar to be ready
p.write("My 1st Song")
time.sleep(1)  # Wait for the input
p.press('enter')
