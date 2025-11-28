import Scene.Camera.Camera;

cbuffer PerFrameCB
{
    uint2 gResolution;
    float2 gInvResolution;
    Camera gShadowCamera;
    Camera gMainCamera;
    float gShadowBias;
}

Texture2D<float> gShadowDepth; // Shadow map depth texture
Texture2D<float> gGBufferDepth; // Scene depth texture
RWTexture2D<float> gShadowMask; // Output shadow mask texture

[numthreads(16, 16, 1)]
void shadowProjection(uint3 dispatchThreadId: SV_DispatchThreadID)
{
    if (any(dispatchThreadId.xy >= gResolution))
        return;
    const uint2 pixelPos = dispatchThreadId.xy;
    const float2 uv = (float2(pixelPos) + 0.5) * gInvResolution;

    // recover GBuffer pos in world space
    float sceneDepth = gGBufferDepth.Load(int3(pixelPos, 0));
    if (sceneDepth >= 1.0)
    {
        gShadowMask[pixelPos] = 1.0;
        return;
    }
    float4 objPosH = float4(uv.x * 2.0 - 1.0, (1.0 - uv.y) * 2.0 - 1.0, sceneDepth, 1.0);
    float4 objPosW = mul(gMainCamera.data.invViewProj, objPosH);
    objPosW /= objPosW.w;

    // project scene geometry pos to light space
    float4 lightSpaceObjPosH = mul(gShadowCamera.getViewProj(), objPosW);
    lightSpaceObjPosH /= lightSpaceObjPosH.w;
    float2 lightSpaceUV = lightSpaceObjPosH.xy * 0.5 + 0.5;
    lightSpaceUV.y = 1.0 - lightSpaceUV.y;
    float shadowSpaceObjectDepth = lightSpaceObjPosH.z;

    if (lightSpaceUV.x < 0.0 || lightSpaceUV.x > 1.0 || lightSpaceUV.y < 0.0 || lightSpaceUV.y > 1.0)
    {
        // outside shadow map
        gShadowMask[pixelPos] = 1.0;
        return;
    }

    // sample shadow map (no need to use a SamplerState, directly indexing is fine)
    uint2 shadowDepthDimensions;
    gShadowDepth.GetDimensions(shadowDepthDimensions.x, shadowDepthDimensions.y);
    float shadowMapDepth = gShadowDepth.Load(int3(lightSpaceUV * shadowDepthDimensions, 0));

    // do a simple shadow test with bias
    float shadow = 1.0;
    if (shadowSpaceObjectDepth - gShadowBias > shadowMapDepth)
    {
        shadow = 0.0;
    }
    gShadowMask[pixelPos] = shadow;
}
