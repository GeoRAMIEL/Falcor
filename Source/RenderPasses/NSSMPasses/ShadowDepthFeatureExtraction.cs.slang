import Scene.Camera.Camera;

cbuffer PerFrameCB
{
    uint2 gResolution;
    float2 gInvResolution;
    Camera gShadowCamera;
}

Texture2D<float> gShadowDepth; // Shadow map depth texture
RWTexture2D<float2> gAvgMap; // Average shadow depth map (in world units)
RWTexture2D<float2> gStdMap; // shadow depth standard deviation map
RWTexture2D<float> gPinholeMap; // pinhole detection map
RWTexture2D<float> gDvgMap; // divergence map

// GATHER_RADIUS should be defined

float getViewSpaceShadowDepth(float shadowDepth)
{
    // Convert shadow depth from [0,1] to view space Z
    // simplify calculation for orthographic camera
    if (gShadowCamera.data.focalLength == 0.0f)
    {
        float zView = gShadowCamera.data.nearZ + shadowDepth * (gShadowCamera.data.farZ - gShadowCamera.data.nearZ);
        return zView;
    }
    else
    {
        float zView = gShadowCamera.data.nearZ * gShadowCamera.data.farZ / (gShadowCamera.data.farZ - shadowDepth * (gShadowCamera.data.farZ - gShadowCamera.data.nearZ));
        return zView;
    }
}

[numthreads(16, 16, 1)]
void mainAvg(uint3 dispatchThreadId: SV_DispatchThreadID)
{
    if (any(dispatchThreadId.xy >= gResolution))
        return;
    const uint2 pixelPos = dispatchThreadId.xy;
    const float2 uv = (float2(pixelPos) + 0.5) * gInvResolution;

    // sample shadow map (no need to use a SamplerState, directly indexing is fine)
    uint2 shadowDepthDimensions;
    gShadowDepth.GetDimensions(shadowDepthDimensions.x, shadowDepthDimensions.y);
    float centerSample = getViewSpaceShadowDepth(gShadowDepth.Load(int3(uv * shadowDepthDimensions, 0)));

    // Accumulate depth samples in a radius
    float neighborSum = 0.0;
    uint neighborCount = 0;
    for (int y = -GATHER_RADIUS; y <= GATHER_RADIUS; ++y)
    {
        for (int x = -GATHER_RADIUS; x <= GATHER_RADIUS; ++x)
        {
            if (x == 0 && y == 0)
                continue; // skip center sample
            float distToCenter = length(float2(x, y));
            if (distToCenter > GATHER_RADIUS)
                continue; // outside gather radius

            int2 offset = int2(x, y);
            float2 offsetUV = uv + float2(offset) / float2(shadowDepthDimensions);
            if (all(offsetUV >= 0.0) && all(offsetUV <= 1.0))
            {
                float sample = getViewSpaceShadowDepth(gShadowDepth.Load(int3(offsetUV * shadowDepthDimensions, 0)));
                neighborSum += sample;
                neighborCount++;
            }
        }
    }
    float averageNoCenter = neighborSum / neighborCount;
    float averageWithCenter = (neighborSum + centerSample) / (neighborCount + 1);
    gAvgMap[pixelPos] = float2(averageNoCenter, averageWithCenter);
}

[numthreads(16, 16, 1)]
void mainStd(uint3 dispatchThreadId : SV_DispatchThreadID)
{
    if (any(dispatchThreadId.xy >= gResolution))
        return;

    const uint2 pixelPos = dispatchThreadId.xy;
    const float2 uv = (float2(pixelPos) + 0.5) * gInvResolution;

    uint2 shadowDepthDimensions;
    gShadowDepth.GetDimensions(shadowDepthDimensions.x, shadowDepthDimensions.y);

    // Read precomputed means: x = mean without center, y = mean with center
    float2 avg = gAvgMap[pixelPos];
    float meanNoCenter   = avg.x;
    float meanWithCenter = avg.y;

    // Accumulate variance
    float neighborVarSum = 0.0;
    uint neighborCount = 0;

    for (int y = -GATHER_RADIUS; y <= GATHER_RADIUS; ++y)
    {
        for (int x = -GATHER_RADIUS; x <= GATHER_RADIUS; ++x)
        {
            int2 offset = int2(x, y);

            if (x == 0 && y == 0)
                continue; // skip center sample

            float distToCenter = length(float2(x, y));
            if (distToCenter > GATHER_RADIUS)
                continue; // outside gather radius

            float2 offsetUV = uv + float2(offset) / float2(shadowDepthDimensions);
            if (!all(offsetUV >= 0.0) || !all(offsetUV <= 1.0))
                continue;

            float neighborSample = getViewSpaceShadowDepth(
                gShadowDepth.Load(int3(offsetUV * shadowDepthDimensions, 0))
            );

            float diff = neighborSample - meanNoCenter;
            neighborVarSum += diff * diff;
            neighborCount++;
        }
    }

    float stdNoCenter   = (neighborCount > 0) ? sqrt(neighborVarSum / neighborCount) : 0.0;

    float centerSample = getViewSpaceShadowDepth(gShadowDepth.Load(int3(uv * shadowDepthDimensions, 0)));
    float varSumWithCenter = neighborVarSum + (centerSample - meanWithCenter) * (centerSample - meanWithCenter);
    float stdWithCenter = (neighborCount > 0) ? sqrt(varSumWithCenter / (neighborCount + 1)) : 0.0;

    gStdMap[pixelPos] = float2(stdNoCenter, stdWithCenter);
}

#define PINHOLE_STDDEV_THRESHOLD 0.1f

[numthreads(16, 16, 1)]
void mainPinholeDetect(uint3 dispatchThreadId : SV_DispatchThreadID)
{
    if (any(dispatchThreadId.xy >= gResolution))
        return;
    const uint2 pixelPos = dispatchThreadId.xy;
    const float2 uv = (float2(pixelPos) + 0.5) * gInvResolution;

    float rawDepth = gShadowDepth.Load(int3(pixelPos, 0));
    if (rawDepth == 0.0 || rawDepth == 1.0)
    {
        gPinholeMap[pixelPos] = 0.0;
        return;
    }

    // Read precomputed average and standard deviation
    float2 avg = gAvgMap[pixelPos];
    float meanNoCenter   = avg.x;
    float meanWithCenter = avg.y;

    float2 std = gStdMap[pixelPos];
    float stdNoCenter = std.x;
    float stdWithCenter = std.y;

    //stdNoCenter = stdNoCenter / (meanNoCenter + 1e-5);
    //stdWithCenter = stdWithCenter / (meanWithCenter + 1e-5);

    // Pinhole detection criterion:
    // Standard deviation including center is high (indicating discontinuity)
    // but standard deviation excluding center is low (indicating that neighbors are relatively flat)
    if (stdWithCenter > PINHOLE_STDDEV_THRESHOLD &&
        stdNoCenter < PINHOLE_STDDEV_THRESHOLD)
    {
        gPinholeMap[pixelPos] = 1.0;
    }
    else
    {
        gPinholeMap[pixelPos] = 0.0;
    }
    /*float pinholeResponse = saturate((stdWithCenter - PINHOLE_STDDEV_THRESHOLD) / PINHOLE_STDDEV_THRESHOLD) *
                            saturate((PINHOLE_STDDEV_THRESHOLD - stdNoCenter) / PINHOLE_STDDEV_THRESHOLD);*/
}

#define DVG_MAX 2.0f
[numthreads(16, 16, 1)]
void mainDivergence(uint3 dispatchThreadId : SV_DispatchThreadID)
{
    if (any(dispatchThreadId.xy >= gResolution))
        return;
    const int2 pixelPos = dispatchThreadId.xy;
    const float2 uv = (float2(pixelPos) + 0.5) * gInvResolution;
    int2 shadowDepthDimensions;
    gShadowDepth.GetDimensions(shadowDepthDimensions.x, shadowDepthDimensions.y);
    
    float rawDepth = gShadowDepth.Load(int3(pixelPos, 0));
    if (rawDepth == 0.0 || rawDepth == 1.0)
    {
        gDvgMap[pixelPos] = 0.0;
        return;
    }
    float centerSample = getViewSpaceShadowDepth(rawDepth);

    float divergence = 0.0;
    int neighborCount = 0;
    for (int y = -1; y <= 1; ++y)
    {
        for (int x = -1; x <= 1; ++x)
        {
            if (x == 0 && y == 0)
                continue; // skip center sample
            int2 offset = int2(x, y);
            int2 neighborPixelPos = dispatchThreadId.xy + int2(offset);
            if (any(neighborPixelPos < 0) || any(neighborPixelPos >= int2(gResolution)))
            {
                continue; // outside texture bounds
            }
            else
            {
                float sample = getViewSpaceShadowDepth(gShadowDepth.Load(int3(neighborPixelPos, 0)));
                divergence += abs(sample - centerSample);
                neighborCount++;
            }
        }
    }
    divergence = divergence / neighborCount;
    divergence = saturate(divergence / DVG_MAX);
    gDvgMap[pixelPos] = divergence;
}
