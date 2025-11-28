import Scene.Camera.Camera;

cbuffer PerFrameCB
{
    uint2 gResolution;
    float2 gInvResolution;
    Camera gShadowCamera;
    Camera gMainCamera;
    float gShadowBias;
}

Texture2D<float> gShadowDepth;      // Shadow map depth texture
Texture2D<float> gGBufferDepth;     // Scene depth texture (view-space depth in [0,1])
Texture2D<float4> gGBufferNormal;   // Scene normal buffer (world-space normal in xyz)

RWTexture2D<float> gShadowMask;     // Output shadow mask texture
RWTexture2D<float> gNdotL;          // Output N dot L
RWTexture2D<float> gBlockerDistance;// World-space distance between receiver and blocker
RWTexture2D<float> gCv;             // Dot product of receiver normal and view direction

[numthreads(16, 16, 1)]
void nssmFeaturePass(uint3 dispatchThreadId: SV_DispatchThreadID)
{
    if (any(dispatchThreadId.xy >= gResolution))
        return;

    const uint2 pixelPos = dispatchThreadId.xy;
    const float2 uv = (float2(pixelPos) + 0.5) * gInvResolution;

    // Recover receiver position from depth.
    float sceneDepth = gGBufferDepth.Load(int3(pixelPos, 0));
    if (sceneDepth >= 1.0)
    {
        // Background: unshadowed and zero features.
        gShadowMask[pixelPos] = 1.0;
        gNdotL[pixelPos] = 0.0;
        gBlockerDistance[pixelPos] = 0.0;
        gCv[pixelPos] = 0.0;
        return;
    }

    // Reconstruct world position from depth and main camera.
    float4 objPosH = float4(uv * 2.0 - 1.0, sceneDepth * 2.0 - 1.0, 1.0);
    float4 objPosW = mul(gMainCamera.data.invViewProj, objPosH);
    objPosW /= objPosW.w;
    float3 posW = objPosW.xyz;

    // Fetch normal (assumed world-space, normalized or close to it).
    float3 N = normalize(gGBufferNormal.Load(int3(pixelPos, 0)).xyz);

    // Derive light direction from shadow camera view direction.
    // We treat shadow camera forward (cameraW) as pointing from light towards the scene,
    // so the light direction L (from point towards light) is -cameraW.
    float3 L = normalize(-gShadowCamera.data.cameraW);

    // Compute shadow projection as in ShadowProjectionPass.
    float4 lightSpaceObjPosH = mul(gShadowCamera.getViewProj(), objPosW);
    lightSpaceObjPosH /= lightSpaceObjPosH.w;
    float2 lightSpaceUV = lightSpaceObjPosH.xy * 0.5 + 0.5;
    float shadowSpaceObjectDepth = lightSpaceObjPosH.z * 0.5 + 0.5;

    // Default feature values.
    float shadow = 1.0;
    float ndotl = saturate(dot(N, L));
    float blockerDist = 0.0;
    float cvVal = 0.0;

    if (lightSpaceUV.x < 0.0 || lightSpaceUV.x > 1.0 || lightSpaceUV.y < 0.0 || lightSpaceUV.y > 1.0)
    {
        // Outside shadow map: treat as unshadowed, leave defaults.
        cvVal = dot(N, normalize(gMainCamera.data.posW - posW));
    }
    else
    {
        // Sample shadow map.
        uint2 shadowDepthDimensions;
        gShadowDepth.GetDimensions(shadowDepthDimensions.x, shadowDepthDimensions.y);
        float shadowMapDepth = gShadowDepth.Load(int3(lightSpaceUV * shadowDepthDimensions, 0));

        // Simple shadow test with bias.
        if (shadowSpaceObjectDepth - gShadowBias > shadowMapDepth)
        {
            shadow = 0.0;

            // Estimate blocker world position along light direction using shadow map depth.
            float4 blockerLightSpaceH = float4(lightSpaceObjPosH.xy, shadowMapDepth * 2.0 - 1.0, 1.0);
            float4 blockerWorldH = mul(gShadowCamera.data.invViewProj, blockerLightSpaceH);
            blockerWorldH /= blockerWorldH.w;
            float3 blockerPosW = blockerWorldH.xyz;

            blockerDist = length(blockerPosW - posW);
        }

        // View direction from receiver towards main camera position.
        float3 V = normalize(gMainCamera.data.posW - posW);
        cvVal = dot(N, V);
    }

    gShadowMask[pixelPos] = shadow;
    gNdotL[pixelPos] = ndotl;
    gBlockerDistance[pixelPos] = blockerDist;
    gCv[pixelPos] = cvVal;
}
