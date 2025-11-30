
SCENE_PATH=/workspace/develop/falcor_scenes/EmeraldSquare_v4_1/EmeraldSquare_Day_v1.pyscene

SHADER_CACHE_PATH=/workspace/develop/Falcor/dappled_light_data_gen/shader_cache

MOGWAI_LOG_VERBOSITY=2

# Generate feature images
echo "<<<<< Starting feature image generation at: $(date) >>>>>"
Mogwai --headless --script=network_feature_gen.py --deferred --scene=$SCENE_PATH --width=2048 --height=1024 --verbosity=$MOGWAI_LOG_VERBOSITY
echo "Feature images generated."

# Render ray-traced ground truth
echo "<<<<< Starting ray-traced ground truth rendering at: $(date) >>>>>"
Mogwai --headless --script=ground_truth_render.py --deferred --scene=$SCENE_PATH --width=2048 --height=1024 --verbosity=$MOGWAI_LOG_VERBOSITY
echo "Ray-traced ground truth rendered."

# Convert renders to KPNSM format
#python3 convert_renders_to_kpnsm_format.py --input_folder=mogwai_renders --output_folder=kpnsm_format
#echo "Renders converted to KPNSM format."

# print end time
echo "<<<<< Data generation finished at: $(date) >>>>>"
