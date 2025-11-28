#pragma once
#include "Falcor.h"
#include "RenderGraph/RenderPass.h"
#include "RenderGraph/RenderPassHelpers.h"

using namespace Falcor;

class ShadowDepthPass : public RenderPass
{
public:
    FALCOR_PLUGIN_CLASS(ShadowDepthPass, "ShadowDepthPass", "Insert pass description here.");

    static ref<ShadowDepthPass> create(ref<Device> pDevice, const Properties& props)
    {
        return make_ref<ShadowDepthPass>(pDevice, props);
    }

    ShadowDepthPass(ref<Device> pDevice, const Properties& props);

    virtual Properties getProperties() const override;
    virtual RenderPassReflection reflect(const CompileData& compileData) override;
    virtual void compile(RenderContext* pRenderContext, const CompileData& compileData) override {}
    virtual void execute(RenderContext* pRenderContext, const RenderData& renderData) override;
    virtual void renderUI(Gui::Widgets& widget) override;
    virtual void setScene(RenderContext* pRenderContext, const ref<Scene>& pScene) override;
    virtual bool onMouseEvent(const MouseEvent& mouseEvent) override { return false; }
    virtual bool onKeyEvent(const KeyboardEvent& keyEvent) override { return false; }

private:
    virtual void parseProperties(const Properties& props);
    virtual void setCullMode(RasterizerState::CullMode mode) { mCullMode = mode; }
    void updateFrameDim(const uint2 frameDim);

    ref<Texture> getOutput(const RenderData& renderData) const;

    void recreatePrograms();

    void bindParameterBlock();

    // Internal state

    ref<Scene> mpScene;
    sigs::Connection mUpdateFlagsConnection; ///< Connection to the UpdateFlags signal.
    /// IScene::UpdateFlags accumulated since last `beginFrame()`
    IScene::UpdateFlags mUpdateFlags = IScene::UpdateFlags::None;

    /// Frames rendered since last change of scene. This is used as random seed.
    uint32_t mFrameCount = 0;
    /// Current frame dimension in pixels. Note this may be different from the window size.
    uint2 mFrameDim = {};
    float2 mInvFrameDim = {};

    // UI variables

    /// Selected output size.
    RenderPassHelpers::IOSize mOutputSizeSelection = RenderPassHelpers::IOSize::Fixed;
    /// Output size in pixels
    uint mOutputSize = 512;
    /// Enable alpha test.
    bool mUseAlphaTest = true;
    /// Force cull mode for all geometry, otherwise set it based on the scene.
    bool mForceCullMode = false;
    /// Cull mode to use for when mForceCullMode is true.
    RasterizerState::CullMode mCullMode = RasterizerState::CullMode::Back;
    /// Shadow camera name (if empty, use the active scene camera)
    std::string mShadowCameraName;

    /// Indicates whether any options that affect the output have changed since last frame.
    bool mOptionsChanged = false;

    ref<Fbo> mpFbo;

    struct
    {
        ref<GraphicsState> pState;
        ref<Program> pProgram;
        ref<ProgramVars> pVars;
    } mDepthPass;

    ref<ParameterBlock> mpShadowDepthBlock;
};
