#pragma once
#include "Falcor.h"
#include "RenderGraph/RenderPass.h"
#include "RenderGraph/RenderPassHelpers.h"

using namespace Falcor;

class ShadowProjectionPass : public RenderPass
{
public:
    FALCOR_PLUGIN_CLASS(ShadowProjectionPass, "ShadowProjectionPass", "Insert pass description here.");

    static ref<ShadowProjectionPass> create(ref<Device> pDevice, const Properties& props)
    {
        return make_ref<ShadowProjectionPass>(pDevice, props);
    }

    ShadowProjectionPass(ref<Device> pDevice, const Properties& props);

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
    void updateFrameDim(const uint2 frameDim);

    ref<Texture> getOutput(const RenderData& renderData) const;

    void recreatePrograms();

    // Internal state

    ref<Scene> mpScene;
    sigs::Connection mUpdateFlagsConnection; ///< Connection to the UpdateFlags signal.
    /// IScene::UpdateFlags accumulated since last `beginFrame()`
    IScene::UpdateFlags mUpdateFlags = IScene::UpdateFlags::None;

    /// Current frame dimension in pixels. Should be the same as the window size at least for now.
    uint2 mFrameDim = {};
    float2 mInvFrameDim = {};

    // UI variables
    /// Shadow camera name (cannot be empty)
    std::string mShadowCameraName;
    /// Shadow Bias
    float mShadowBias = 0.005f;

    /// Indicates whether any options that affect the output have changed since last frame.
    bool mOptionsChanged = false;

    ref<Fbo> mpFbo;

    ref<Program> mpProgram;
    ref<ProgramVars> mpVars;
    ref<ComputeState> mpState;

    ref<ParameterBlock> mpShadowProjectionBlock;
};
