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

RWTexture2D<float4> gShadowMask;    // Output shadow mask texture
RWTexture2D<float> gCv;             // Dot product of receiver normal and view direction
RWTexture2D<float> gCe;             // Output N dot L
RWTexture2D<float> gDistRtoB;       // World-space distance between receiver and blocker
RWTexture2D<float> gDistEtoR;       // World-space distance between receiver and emitter
RWTexture2D<float> gDistVtoR;       // World-space distance between receiver and view point
RWTexture2D<float> gDistEtoB;       // World-space distance between emitter and blocker
RWTexture2D<float4> gPosW;          // World position of receiver


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
        gShadowMask[pixelPos] = float4(1.0, 1.0, 0.0, 1.0);
        gCv[pixelPos] = 0.0;
        gCe[pixelPos] = 0.0;
        gDistRtoB[pixelPos] = 0.0;
        gDistEtoR[pixelPos] = 0.0;
        gDistVtoR[pixelPos] = 0.0;
        gDistEtoB[pixelPos] = 0.0;
        gPosW[pixelPos] = float4(0.0, 0.0, 0.0, 0.0);
        return;
    }

    // Reconstruct world position from depth and main camera.
    float4 objPosH = float4(uv.x * 2.0 - 1.0, (1.0 - uv.y) * 2.0 - 1.0, sceneDepth, 1.0);
    float4 objPosW = mul(gMainCamera.data.invViewProj, objPosH);
    objPosW /= objPosW.w;
    float3 posW = objPosW.xyz;

    // Fetch world space normal
    float3 N = normalize(gGBufferNormal.Load(int3(pixelPos, 0)).xyz);

    // Derive light direction from shadow camera view direction.
    // We treat shadow camera forward (cameraW) as pointing from light towards the scene,
    // so the light direction L (from point towards light) is -cameraW.
    float3 L = normalize(-gShadowCamera.data.cameraW);

    // Compute shadow projection as in ShadowProjectionPass.
    float4 lightSpaceObjPosH = mul(gShadowCamera.getViewProj(), objPosW);
    lightSpaceObjPosH /= lightSpaceObjPosH.w;
    float2 lightSpaceUV = lightSpaceObjPosH.xy * 0.5 + 0.5;
    lightSpaceUV.y = 1.0 - lightSpaceUV.y;
    float shadowSpaceObjectDepth = lightSpaceObjPosH.z;

    // Default feature values.
    float shadow = 1.0;
    // View direction from receiver towards main camera position.
    float3 V = normalize(gMainCamera.data.posW - posW);
    float ndotv = dot(N, V);
    float ndotl = dot(N, L);
    // TODO: do we need to set shadowMask to 0 for ndotl<0 pixels?
    // Use a dummy light source position to conform with KPNSM expectations.
    float3 lightPosW = gShadowCamera.data.posW - L * 1000;
    float distRtoB = 0.0; // Treat blocker pos as reveiver pos by default
    float distEtoR = length(lightPosW - posW);
    float distVtoR = length(gMainCamera.data.posW - posW);
    float distEtoB = length(lightPosW - posW); // Treat blocker pos as reveiver pos by default

    if (lightSpaceUV.x >= 0.0 && lightSpaceUV.x <= 1.0 && lightSpaceUV.y >= 0.0 && lightSpaceUV.y <= 1.0)
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
            float4 blockerLightSpaceH = float4(lightSpaceObjPosH.xy, shadowMapDepth, 1.0);
            float4 blockerWorldH = mul(gShadowCamera.data.invViewProj, blockerLightSpaceH);
            blockerWorldH /= blockerWorldH.w;
            float3 blockerPosW = blockerWorldH.xyz;

            distRtoB = length(blockerPosW - posW);
            distEtoB = length(lightPosW - blockerPosW);
        }
    }

    gShadowMask[pixelPos] = float4(shadow, shadow, distRtoB, 1.0);
    gCv[pixelPos] = ndotv;
    gCe[pixelPos] = ndotl;
    gDistRtoB[pixelPos] = distRtoB;
    gDistEtoR[pixelPos] = distEtoR;
    gDistVtoR[pixelPos] = distVtoR;
    gDistEtoB[pixelPos] = distEtoB;
    gPosW[pixelPos] = float4(posW, 1.0);
}
