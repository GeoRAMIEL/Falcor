from falcor import *

# randomization setting format
#[
#    {
#        "mainCamera": {
#            "position": [ -26.538925785515005, 5.550253543686567, 45.633266010163524 ],
#            "target": [ -27.3023573753774, 4.596173390729017, 30.783376941272767]
#        },
#        "sunCamera": {
#            "position": [ -26.538925785515005, 55.550253543686566, 45.633266010163524 ],
#            "target": [ -4.65926217645762, -37.027741116411974, 76.46499033867387 ]
#        },
#        "sunLight": {
#            "direction": [ 0.21879663609057384, -0.9257799466009854, 0.3083172432851035 ]
#        }
#    },
#    ...
#]

def apply_randomization(scene, randomization_settings, settingIndex):
    if settingIndex >= len(randomization_settings):
        print(f"No more randomization settings available for settingIndex={settingIndex}")
        return
    setting = randomization_settings[settingIndex]
    mainCam = scene.cameras[0]  # assuming main camera is the first added
    sunCam = scene.cameras[1] # assuming sun camera is the second added
    sunLight = scene.getLight('Sun Light Distant')

    #print(f"mainCam pos: {setting['mainCamera']['position']}, target: {setting['mainCamera']['target']}")
    
    mainCam.position = float3(setting['mainCamera']['position'][0], setting['mainCamera']['position'][1], setting['mainCamera']['position'][2])
    mainCam.target = float3(setting['mainCamera']['target'][0], setting['mainCamera']['target'][1], setting['mainCamera']['target'][2])
    sunCam.position = float3(setting['sunCamera']['position'][0], setting['sunCamera']['position'][1], setting['sunCamera']['position'][2])
    sunCam.target = float3(setting['sunCamera']['target'][0], setting['sunCamera']['target'][1], setting['sunCamera']['target'][2])

    sunLight.direction = float3(setting['sunLight']['direction'][0], setting['sunLight']['direction'][1], setting['sunLight']['direction'][2])

    if sunLight.direction.y <= -0.98:
        sunCam.up = float3(0.0, 0.0, 1.0)
    else:
        sunCam.up = float3(0.0, 1.0, 0.0)
