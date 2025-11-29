#include "ShadowDepthFeatureExtraction.h"
#include "RenderGraph/RenderPassStandardFlags.h"

namespace
{
const std::string kShadowDepthFeatureExtractionProgramFile = "RenderPasses/NSSMPasses/ShadowDepthFeatureExtraction.cs.slang";

const std::string kShadowDepthName = "shadowDepth";
const std::string kAvgMapName = "avgMap";
const std::string kStdMapName = "stdMap";
const std::string kPinholeMapName = "pinholeMap";
const std::string kDivergenceMapName = "dvgMap";
// Scripting options.
const char kMainCamera[] = "mainCamera";
const char kOutputSize[] = "outputSize";
const char kShadowCamera[] = "shadowCamera";
const char kVarRadiusW[] = "varRadiusW";

const std::string kShadowDepthFeatureExtractionData = "gShadowDepthFeatureExtractionData";
} // namespace

ShadowDepthFeatureExtraction::ShadowDepthFeatureExtraction(ref<Device> pDevice, const Properties& props) : RenderPass(pDevice)
{
    parseProperties(props);

    // Initialize compute state
    mpAvgState = ComputeState::create(mpDevice);
    mpStdState = ComputeState::create(mpDevice);
    mpPinHoleDetectState = ComputeState::create(mpDevice);
    mpDivergenceState = ComputeState::create(mpDevice);
}

Properties ShadowDepthFeatureExtraction::getProperties() const
{
    Properties props;
    props[kShadowCamera] = mShadowCameraName;
    props[kOutputSize] = mOutputSize;
    props[kVarRadiusW] = mVarRadiusW;
    return props;
}

RenderPassReflection ShadowDepthFeatureExtraction::reflect(const CompileData& compileData)
{
    const uint2 sz = {mOutputSize, mOutputSize};

    RenderPassReflection reflector;
    reflector.addInput(kShadowDepthName, "Shadow Depth Map")
        .bindFlags(ResourceBindFlags::ShaderResource);

    reflector.addOutput(kAvgMapName, "Average Depth")
        .format(ResourceFormat::RG32Float)
        .bindFlags(ResourceBindFlags::UnorderedAccess | ResourceBindFlags::ShaderResource)
        .texture2D(sz.x, sz.y);
    reflector.addOutput(kStdMapName, "Standard Deviation Map")
        .format(ResourceFormat::RG32Float)
        .bindFlags(ResourceBindFlags::UnorderedAccess | ResourceBindFlags::ShaderResource)
        .texture2D(sz.x, sz.y);
    reflector.addOutput(kPinholeMapName, "Pinhole Detection Map")
        .format(ResourceFormat::R8Unorm)
        .bindFlags(ResourceBindFlags::UnorderedAccess | ResourceBindFlags::ShaderResource)
        .texture2D(sz.x, sz.y);
    reflector.addOutput(kDivergenceMapName, "Divergence Map")
        .format(ResourceFormat::R32Float)
        .bindFlags(ResourceBindFlags::UnorderedAccess | ResourceBindFlags::ShaderResource)
        .texture2D(sz.x, sz.y);
    return reflector;
}

void ShadowDepthFeatureExtraction::execute(RenderContext* pRenderContext, const RenderData& renderData)
{
    // renderData holds the requested resources
    // auto& pTexture = renderData.getTexture("src");

    // Update refresh flag if options that affect the output have changed.
    auto& dict = renderData.getDictionary();
    if (mOptionsChanged)
    {
        auto flags = dict.getValue(kRenderPassRefreshFlags, RenderPassRefreshFlags::None);
        dict[Falcor::kRenderPassRefreshFlags] = flags | Falcor::RenderPassRefreshFlags::RenderOptionsChanged;
        mOptionsChanged = false;
    }

    // get input and output textures
    auto pShadowDepthTex = renderData.getTexture(kShadowDepthName);
    auto pAvgMap = renderData.getTexture(kAvgMapName);
    auto pStdMap = renderData.getTexture(kStdMapName);
    auto pPinholeMap = renderData.getTexture(kPinholeMapName);
    auto pDvgMap = renderData.getTexture(kDivergenceMapName);

    // Update frame dimension based on render pass output.
    FALCOR_ASSERT(pPinholeMap && pAvgMap && pStdMap && pDvgMap);
    updateFrameDim(uint2(pPinholeMap->getWidth(), pPinholeMap->getHeight()));
    // clear target
    pRenderContext->clearUAV(pAvgMap->getUAV().get(), float4(0.f, 0.f, 0.f, 0.f));
    pRenderContext->clearUAV(pStdMap->getUAV().get(), float4(0.f, 0.f, 0.f, 0.f));
    pRenderContext->clearUAV(pPinholeMap->getUAV().get(), float4(0.f, 0.f, 0.f, 0.f));
    pRenderContext->clearUAV(pDvgMap->getUAV().get(), float4(0.f, 0.f, 0.f, 0.f));

    // If there is no scene, clear target and return.
    if (mpScene == nullptr)
    {
        return;
    }

    // Check for scene changes.
    if (is_set(mpScene->getUpdates(), IScene::UpdateFlags::RecompileNeeded))
    {
        recreatePrograms();
    }

    // find shadow camera
    ref<Camera> pShadowCam;
    const std::vector<ref<Camera>>& allCameras = mpScene->getCameras();
    for (const auto& pCam : allCameras)
    {
        if (pCam->getName() == mShadowCameraName)
        {
            pShadowCam = pCam;
            break;
        }
    }
    if (!pShadowCam)
    {
        return;
    }

    // calculate gathering radius in pixels using camera data
    float halfOrthoSize = length(pShadowCam->getData().posW - pShadowCam->getData().target) * 0.5f;
    int gatherRadiusInPixels = std::max(int((mVarRadiusW / halfOrthoSize) * float(mOutputSize)), 1);
    gatherRadiusInPixels = std::min(gatherRadiusInPixels, 128); // clamp to max radius
    DefineList defines;
    defines.add(mpScene->getSceneDefines());
    defines.add("GATHER_RADIUS", std::to_string(gatherRadiusInPixels));

    // Create depth pass program.
    if (!mpAvgProgram)
    {
        mpAvgProgram = Program::createCompute(mpDevice,
                        kShadowDepthFeatureExtractionProgramFile,
                        "mainAvg",
                        defines,
                        SlangCompilerFlags::TreatWarningsAsErrors);
        mpAvgVars = ProgramVars::create(mpDevice, mpAvgProgram->getReflector());
    }
    if (!mpStdProgram)
    {
        mpStdProgram = Program::createCompute(mpDevice,
                        kShadowDepthFeatureExtractionProgramFile,
                        "mainStd",
                        defines,
                        SlangCompilerFlags::TreatWarningsAsErrors);
        mpStdVars = ProgramVars::create(mpDevice, mpStdProgram->getReflector());
    }
    if (!mpPinHoleDetectProgram)
    {
        mpPinHoleDetectProgram = Program::createCompute(mpDevice,
                        kShadowDepthFeatureExtractionProgramFile,
                        "mainPinholeDetect",
                        defines,
                        SlangCompilerFlags::TreatWarningsAsErrors);
        mpPinHoleDetectVars = ProgramVars::create(mpDevice, mpPinHoleDetectProgram->getReflector());
    }
    if (!mpDivergenceProgram)
    {
        mpDivergenceProgram = Program::createCompute(mpDevice,
                        kShadowDepthFeatureExtractionProgramFile,
                        "mainDivergence",
                        defines,
                        SlangCompilerFlags::TreatWarningsAsErrors);
        mpDivergenceVars = ProgramVars::create(mpDevice, mpDivergenceProgram->getReflector());
    }

    // set shader parameters
    auto avgVar = mpAvgVars->getRootVar();
    avgVar["gShadowDepth"] = pShadowDepthTex;
    avgVar["gAvgMap"] = pAvgMap;
    avgVar["PerFrameCB"]["gResolution"] = mFrameDim;
    avgVar["PerFrameCB"]["gInvResolution"] = mInvFrameDim;
    pShadowCam->bindShaderData(avgVar["PerFrameCB"]["gShadowCamera"]);

    auto stdVar = mpStdVars->getRootVar();
    stdVar["gShadowDepth"] = pShadowDepthTex;
    stdVar["gAvgMap"] = pAvgMap;
    stdVar["gStdMap"] = pStdMap;
    stdVar["PerFrameCB"]["gResolution"] = mFrameDim;
    stdVar["PerFrameCB"]["gInvResolution"] = mInvFrameDim;
    pShadowCam->bindShaderData(stdVar["PerFrameCB"]["gShadowCamera"]);

    auto pinholeVar = mpPinHoleDetectVars->getRootVar();
    pinholeVar["gShadowDepth"] = pShadowDepthTex;
    pinholeVar["gAvgMap"] = pAvgMap;
    pinholeVar["gStdMap"] = pStdMap;
    pinholeVar["gPinholeMap"] = pPinholeMap;
    pinholeVar["PerFrameCB"]["gResolution"] = mFrameDim;
    pinholeVar["PerFrameCB"]["gInvResolution"] = mInvFrameDim;
    pShadowCam->bindShaderData(pinholeVar["PerFrameCB"]["gShadowCamera"]);

    auto dvgVar = mpDivergenceVars->getRootVar();
    dvgVar["gShadowDepth"] = pShadowDepthTex;
    dvgVar["gDvgMap"] = pDvgMap;
    dvgVar["PerFrameCB"]["gResolution"] = mFrameDim;
    dvgVar["PerFrameCB"]["gInvResolution"] = mInvFrameDim;
    pShadowCam->bindShaderData(dvgVar["PerFrameCB"]["gShadowCamera"]);

    // dispatch CS
    FALCOR_ASSERT(mpAvgProgram && mpStdProgram && mpPinHoleDetectProgram);
    // Calculate average depth
    uint3 numGroups = div_round_up(uint3(mFrameDim.x, mFrameDim.y, 1u), mpAvgProgram->getReflector()->getThreadGroupSize());
    mpAvgState->setProgram(mpAvgProgram);
    pRenderContext->dispatch(mpAvgState.get(), mpAvgVars.get(), numGroups);
    // Calculate standard deviation
    numGroups = div_round_up(uint3(mFrameDim.x, mFrameDim.y, 1u), mpStdProgram->getReflector()->getThreadGroupSize());
    mpStdState->setProgram(mpStdProgram);
    pRenderContext->dispatch(mpStdState.get(), mpStdVars.get(), numGroups);
    // Pinhole detection
    numGroups = div_round_up(uint3(mFrameDim.x, mFrameDim.y, 1u), mpPinHoleDetectProgram->getReflector()->getThreadGroupSize());
    mpPinHoleDetectState->setProgram(mpPinHoleDetectProgram);
    pRenderContext->dispatch(mpPinHoleDetectState.get(), mpPinHoleDetectVars.get(), numGroups);
    // Divergence map calculation
    numGroups = div_round_up(uint3(mFrameDim.x, mFrameDim.y, 1u), mpDivergenceProgram->getReflector()->getThreadGroupSize());
    mpDivergenceState->setProgram(mpDivergenceProgram);
    pRenderContext->dispatch(mpDivergenceState.get(), mpDivergenceVars.get(), numGroups);
}

void ShadowDepthFeatureExtraction::renderUI(Gui::Widgets& widget)
{
    // Controls for output size.
    // SKIP this, not using UI
}

void ShadowDepthFeatureExtraction::parseProperties(const Properties& props)
{
    for (const auto& [key, value] : props)
    {
        if (key == kShadowCamera)
            mShadowCameraName = (std::string)value;
        else if (key == kOutputSize)
            mOutputSize = (uint)value;
        else if (key == kVarRadiusW)
            mVarRadiusW = (float)value;
    }
}

void ShadowDepthFeatureExtraction::setScene(RenderContext* pRenderContext, const ref<Scene>& pScene)
{
    mUpdateFlagsConnection = {};
    mUpdateFlags = IScene::UpdateFlags::None;

    mpScene = pScene;

    if (pScene)
    {
        mUpdateFlagsConnection = mpScene->getUpdateFlagsSignal().connect([&](IScene::UpdateFlags flags) { mUpdateFlags |= flags; });
    }

    recreatePrograms();
}

void ShadowDepthFeatureExtraction::recreatePrograms()
{
    mpAvgProgram = nullptr;
    mpAvgVars = nullptr;
    mpStdProgram = nullptr;
    mpStdVars = nullptr;
    mpPinHoleDetectProgram = nullptr;
    mpPinHoleDetectVars = nullptr;
    mpDivergenceProgram = nullptr;
    mpDivergenceVars = nullptr;
}

void ShadowDepthFeatureExtraction::updateFrameDim(const uint2 frameDim)
{
    FALCOR_ASSERT(frameDim.x > 0 && frameDim.y > 0);
    mFrameDim = frameDim;
    mInvFrameDim = 1.f / float2(frameDim);
}
