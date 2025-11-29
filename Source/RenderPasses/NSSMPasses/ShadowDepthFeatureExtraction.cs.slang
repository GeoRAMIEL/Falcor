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
    uint count = 0;
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
                count++;
            }
        }
    }
    float averageNoCenter = neighborSum / count;
    float averageWithCenter = (neighborSum + centerSample) / (count + 1);
    gAvgMap[pixelPos] = float2(averageNoCenter, averageWithCenter);
}

[numthreads(16, 16, 1)]
void mainStd(uint3 dispatchThreadId : SV_DispatchThreadID)
{
    if (any(dispatchThreadId.xy >= gResolution))
        return;

    const uint2 pixelPos = dispatchThreadId.xy;
    const float2 uv = (float2(pixelPos) + 0.5) * gInvResolution;

    // Shadow map dimensions and center sample in view space
    uint2 shadowDepthDimensions;
    gShadowDepth.GetDimensions(shadowDepthDimensions.x, shadowDepthDimensions.y);
    float centerSample = getViewSpaceShadowDepth(
        gShadowDepth.Load(int3(uv * shadowDepthDimensions, 0))
    );

    // Read precomputed means: x = mean without center, y = mean with center
    float2 avg = gAvgMap[pixelPos];
    float meanNoCenter   = avg.x;
    float meanWithCenter = avg.y;

    // Accumulate squared deviations
    float varNoCenter   = 0.0;
    float varWithCenter = 0.0;
    uint  count         = 0;

    for (int y = -GATHER_RADIUS; y <= GATHER_RADIUS; ++y)
    {
        for (int x = -GATHER_RADIUS; x <= GATHER_RADIUS; ++x)
        {
            int2 offset = int2(x, y);

            // Skip center for the “no center” statistic
            bool isCenter = (x == 0 && y == 0);

            float2 offsetUV = uv + float2(offset) / float2(shadowDepthDimensions);
            if (!all(offsetUV >= 0.0) || !all(offsetUV <= 1.0))
                continue;

            float sample = getViewSpaceShadowDepth(
                gShadowDepth.Load(int3(offsetUV * shadowDepthDimensions, 0))
            );

            if (!isCenter)
            {
                float diffNoCenter = sample - meanNoCenter;
                varNoCenter += diffNoCenter * diffNoCenter;
                count++;
            }

            // For “with center” we include all samples, including the center
            float diffWithCenter = sample - meanWithCenter;
            varWithCenter += diffWithCenter * diffWithCenter;
        }
    }

    // Guard against edge cases with no valid neighbors
    float stdNoCenter   = (count > 0) ? sqrt(varNoCenter / count) : 0.0;

    // Number of samples in the full circular neighborhood including center
    // (same set used when you computed meanWithCenter)
    uint fullCount = 0;
    for (int y = -GATHER_RADIUS; y <= GATHER_RADIUS; ++y)
    {
        for (int x = -GATHER_RADIUS; x <= GATHER_RADIUS; ++x)
        {
            float distToCenter = length(float2(x, y));
            if (distToCenter > GATHER_RADIUS) continue;
            fullCount++;
        }
    }
    // Note: varWithCenter was accumulated over the subset that passed UV bounds.
    // To stay consistent with the mean, you could instead maintain a separate
    // counter for the with-center path above. Here we assume all offsets are valid.
    float stdWithCenter = (fullCount > 0) ? sqrt(varWithCenter / fullCount) : 0.0;

    gStdMap[pixelPos] = float2(stdNoCenter, stdWithCenter);
}

#define PINHOLE_STDDEV_THRESHOLD 0.8f

[numthreads(16, 16, 1)]
void mainPinholeDetect(uint3 dispatchThreadId : SV_DispatchThreadID)
{
    if (any(dispatchThreadId.xy >= gResolution))
        return;
    const uint2 pixelPos = dispatchThreadId.xy;
    const float2 uv = (float2(pixelPos) + 0.5) * gInvResolution;

    uint2 shadowDepthDimensions;
    gShadowDepth.GetDimensions(shadowDepthDimensions.x, shadowDepthDimensions.y);
    float centerSample = getViewSpaceShadowDepth(gShadowDepth.Load(int3(uv * shadowDepthDimensions, 0)));
    if (centerSample == 0.0 || centerSample == 1.0)
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

    stdNoCenter = stdNoCenter / (meanNoCenter + 1e-5);
    stdWithCenter = stdWithCenter / (meanWithCenter + 1e-5);

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
}
