#pragma once
#include "Falcor.h"
#include "RenderGraph/RenderPass.h"
#include "RenderGraph/RenderPassHelpers.h"

using namespace Falcor;

class ShadowDepthFeatureExtraction : public RenderPass
{
public:
    FALCOR_PLUGIN_CLASS(ShadowDepthFeatureExtraction, "ShadowDepthFeatureExtraction", "Insert pass description here.");

    static ref<ShadowDepthFeatureExtraction> create(ref<Device> pDevice, const Properties& props)
    {
        return make_ref<ShadowDepthFeatureExtraction>(pDevice, props);
    }

    ShadowDepthFeatureExtraction(ref<Device> pDevice, const Properties& props);

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
    /// Variance radius in world units
    float mVarRadiusW = 0.3f;
    /// Output size
    uint mOutputSize = 512;

    /// Indicates whether any options that affect the output have changed since last frame.
    bool mOptionsChanged = false;

    ref<Program> mpAvgProgram; // average depth program
    ref<ProgramVars> mpAvgVars;
    ref<ComputeState> mpAvgState;

    ref<Program> mpStdProgram; // standard deviation program
    ref<ProgramVars> mpStdVars;
    ref<ComputeState> mpStdState;

    ref<Program> mpPinHoleDetectProgram; // pinhole detection program
    ref<ProgramVars> mpPinHoleDetectVars;
    ref<ComputeState> mpPinHoleDetectState;
};
