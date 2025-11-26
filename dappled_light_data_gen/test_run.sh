#SCENE_PATH=/workspace/develop/Falcor/media/test_scenes/cornell_box_bunny.pyscene
#SCENE_PATH=/workspace/develop/Falcor/media/test_scenes/grey_and_white_room/grey_and_white_room.pyscene
#SCENE_PATH=/workspace/develop/Falcor/media/Arcade/Arcade.pyscene
SCENE_PATH=/workspace/develop/Falcor/dappled_light_data_gen/test_scenes/cornell_box_bunny.pyscene
Mogwai --headless --script=test_mogwai.py --deferred --scene=$SCENE_PATH --width=1280 --height=720 --verbosity=2
echo "Test run completed."
