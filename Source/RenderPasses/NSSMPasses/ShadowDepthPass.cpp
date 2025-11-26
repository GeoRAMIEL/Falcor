#include "ShadowDepthPass.h"
#include "RenderGraph/RenderPassStandardFlags.h"

namespace
{
const std::string kDepthPassProgramFile = "RenderPasses/NSSMPasses/ShadowDepth.3d.slang";
const RasterizerState::CullMode kDefaultCullMode = RasterizerState::CullMode::Back;

const std::string kDepthName = "shadowDepth";
// Scripting options.
const char kOutputSize[] = "outputSize";
const char kFixedOutputSize[] = "fixedOutputSize";
const char kSampleCount[] = "sampleCount";
const char kUseAlphaTest[] = "useAlphaTest";
const char kForceCullMode[] = "forceCullMode";
const char kCullMode[] = "cull";
const char kShadowCamera[] = "shadowCamera";

const std::string kShadowDepthPassData = "gShadowDepthPassData";
} // namespace

extern "C" FALCOR_API_EXPORT void registerPlugin(Falcor::PluginRegistry& registry)
{
    registry.registerClass<RenderPass, ShadowDepthPass>();
}

ShadowDepthPass::ShadowDepthPass(ref<Device> pDevice, const Properties& props) : RenderPass(pDevice)
{
    parseProperties(props);

    // Initialize graphics state
    mDepthPass.pState = GraphicsState::create(mpDevice);

    // Set depth function
    //DepthStencilState::Desc dsDesc;
    //dsDesc.setDepthFunc(ComparisonFunc::LessEqual).setDepthWriteMask(false);
    //ref<DepthStencilState> pDsState = DepthStencilState::create(dsDesc);
    //mDepthPass.pState->setDepthStencilState(pDsState);

    mpFbo = Fbo::create(mpDevice);
}

Properties ShadowDepthPass::getProperties() const
{
    Properties props;
    props[kOutputSize] = mOutputSizeSelection;
    if (mOutputSizeSelection == RenderPassHelpers::IOSize::Fixed)
        props[kFixedOutputSize] = mFixedOutputSize;
    props[kUseAlphaTest] = mUseAlphaTest;
    props[kForceCullMode] = mForceCullMode;
    props[kCullMode] = mCullMode;
    props[kShadowCamera] = mShadowCameraName;
    return props;
}

RenderPassReflection ShadowDepthPass::reflect(const CompileData& compileData)
{
    const uint2 sz = RenderPassHelpers::calculateIOSize(mOutputSizeSelection, mFixedOutputSize, compileData.defaultTexDims);
    
    RenderPassReflection reflector;
    reflector.addOutput(kDepthName, "Depth buffer")
        .format(ResourceFormat::D32Float)
        .bindFlags(ResourceBindFlags::DepthStencil)
        .texture2D(sz.x, sz.y);
    return reflector;
}

void ShadowDepthPass::execute(RenderContext* pRenderContext, const RenderData& renderData)
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

    // Update frame dimension based on render pass output.
    auto pDepth = renderData.getTexture(kDepthName);
    FALCOR_ASSERT(pDepth);
    updateFrameDim(uint2(pDepth->getWidth(), pDepth->getHeight()));

    // Clear depth buffer.
    pRenderContext->clearDsv(pDepth->getDSV().get(), 1.f, 0);

    // If there is no scene, clear depth buffer and return.
    if (mpScene == nullptr)
    {
        return;
    }

    const RasterizerState::CullMode cullMode = mForceCullMode ? mCullMode : kDefaultCullMode;

    // Check for scene changes.
    if (is_set(mpScene->getUpdates(), IScene::UpdateFlags::RecompileNeeded))
    {
        recreatePrograms();
    }

    // Depth pass.
    {
        // Create depth pass program.
        if (!mDepthPass.pProgram)
        {
            ProgramDesc desc;
            desc.addShaderModules(mpScene->getShaderModules());
            desc.addShaderLibrary(kDepthPassProgramFile).vsEntry("vsMain").psEntry("psMain");
            desc.addTypeConformances(mpScene->getTypeConformances());

            mDepthPass.pProgram = Program::create(mpDevice, desc, mpScene->getSceneDefines());
            mDepthPass.pState->setProgram(mDepthPass.pProgram);
        }

        // Set program defines.
        mDepthPass.pState->getProgram()->addDefine("USE_ALPHA_TEST", mUseAlphaTest ? "1" : "0");

        // Create program vars.
        if (!mDepthPass.pVars)
            mDepthPass.pVars = ProgramVars::create(mpDevice, mDepthPass.pProgram.get());

        mpFbo->attachDepthStencilTarget(pDepth);
        mDepthPass.pState->setFbo(mpFbo);

        if (!mpShadowDepthBlock)
        {
            ref<const ParameterBlockReflection> pReflection = mDepthPass.pProgram->getReflector()->getParameterBlock(kShadowDepthPassData);
            FALCOR_ASSERT(pReflection);
            mpShadowDepthBlock = ParameterBlock::create(mpDevice, pReflection);

            bindParameterBlock();
        }

        mDepthPass.pVars->setParameterBlock(kShadowDepthPassData, mpShadowDepthBlock);

        mpScene->rasterize(pRenderContext, mDepthPass.pState.get(), mDepthPass.pVars.get(), cullMode);
    }

    mFrameCount++;
}

void ShadowDepthPass::bindParameterBlock()
{
    auto var = mpShadowDepthBlock->getRootVar();

    if (!mpScene)
        return;
    
    if (mShadowCameraName.empty())
    {
        if (mpScene->getCamera())
            mpScene->getCamera()->bindShaderData(var[kShadowCamera]);
    }
    else
    {
        const std::vector<ref<Camera>>& allCameras = mpScene->getCameras();
        for (const auto& pCam : allCameras)
        {
            if (pCam->getName() == mShadowCameraName)
            {
                pCam->bindShaderData(var[kShadowCamera]);
                break;
            }
        }
    }
}

void ShadowDepthPass::renderUI(Gui::Widgets& widget)
{
    // Controls for output size.
    // When output size requirements change, we'll trigger a graph recompile to update the render pass I/O sizes.
    if (widget.dropdown("Output size", mOutputSizeSelection))
        requestRecompile();
    if (mOutputSizeSelection == RenderPassHelpers::IOSize::Fixed)
    {
        if (widget.var("Size in pixels", mFixedOutputSize, 32u, 16384u))
            requestRecompile();
    }

    // Misc controls.
    mOptionsChanged |= widget.checkbox("Alpha Test", mUseAlphaTest);
    widget.tooltip("Use alpha testing on non-opaque triangles.");

    // Cull mode controls.
    mOptionsChanged |= widget.checkbox("Force cull mode", mForceCullMode);
    widget.tooltip(
        "Enable this option to override the default cull mode.\n\n"
        "Otherwise the default for rasterization is to cull backfacing geometry, "
        "and for ray tracing to disable culling.",
        true
    );

    if (mForceCullMode)
    {
        if (auto cullMode = mCullMode; widget.dropdown("Cull mode", cullMode))
        {
            setCullMode(cullMode);
            mOptionsChanged = true;
        }
    }
}

void ShadowDepthPass::parseProperties(const Properties& props)
{
    for (const auto& [key, value] : props)
    {
        if (key == kOutputSize)
            mOutputSizeSelection = value;
        else if (key == kFixedOutputSize)
            mFixedOutputSize = value;
        else if (key == kUseAlphaTest)
            mUseAlphaTest = value;
        else if (key == kForceCullMode)
            mForceCullMode = value;
        else if (key == kCullMode)
            mCullMode = value;
        else if (key == kShadowCamera)
            mShadowCameraName = (std::string)value;
    }
}

void ShadowDepthPass::setScene(RenderContext* pRenderContext, const ref<Scene>& pScene)
{
    mUpdateFlagsConnection = {};
    mUpdateFlags = IScene::UpdateFlags::None;

    mpScene = pScene;
    mFrameCount = 0;

    if (pScene)
    {
        mUpdateFlagsConnection = mpScene->getUpdateFlagsSignal().connect([&](IScene::UpdateFlags flags) { mUpdateFlags |= flags; });
    }

    recreatePrograms();
}

void ShadowDepthPass::recreatePrograms()
{
    mDepthPass.pProgram = nullptr;
    mDepthPass.pVars = nullptr;
}

void ShadowDepthPass::updateFrameDim(const uint2 frameDim)
{
    FALCOR_ASSERT(frameDim.x > 0 && frameDim.y > 0);
    mFrameDim = frameDim;
    mInvFrameDim = 1.f / float2(frameDim);

    // Update sample generator for camera jitter.
    if (mpScene)
        mpScene->getCamera()->setPatternGenerator(nullptr, mInvFrameDim);
}

ref<Texture> ShadowDepthPass::getOutput(const RenderData& renderData) const
{
    // This helper fetches the render pass output with the given name and verifies it has the correct size.
    FALCOR_ASSERT(mFrameDim.x > 0 && mFrameDim.y > 0);
    auto pTex = renderData.getTexture(kDepthName);
    if (pTex && (pTex->getWidth() != mFrameDim.x || pTex->getHeight() != mFrameDim.y))
    {
        FALCOR_THROW("ShadowDepthPass: Pass output has mismatching size.");
    }
    return pTex;
}