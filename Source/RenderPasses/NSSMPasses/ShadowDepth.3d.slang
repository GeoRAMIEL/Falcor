import Scene.Raster;

struct ShadowDepthPassData
{
    Camera shadowCamera;
};
ParameterBlock<ShadowDepthPassData> gShadowDepthPassData;

// modified based on Scene/Raster.slang
VSOut vsMain(VSIn vIn)
{
    VSOut vOut;
    const GeometryInstanceID instanceID = { vIn.instanceID };

    float4x4 worldMat = gScene.getWorldMatrix(instanceID);
    float3 posW = mul(worldMat, float4(vIn.pos, 1.f)).xyz;
    vOut.posW = posW;
    vOut.posH = mul(gShadowDepthPassData.shadowCamera.getViewProj(), float4(posW, 1.f));

    vOut.instanceID = instanceID;
    vOut.materialID = gScene.getMaterialID(instanceID);

    vOut.texC = vIn.texC;
    vOut.normalW = mul(gScene.getInverseTransposeWorldMatrix(instanceID), vIn.unpack().normal);
    float4 tangent = vIn.unpack().tangent;
    vOut.tangentW = float4(mul((float3x3)gScene.getWorldMatrix(instanceID), tangent.xyz), tangent.w);

    // Compute the vertex position in the previous frame.
    float3 prevPos = vIn.pos;
    GeometryInstanceData instance = gScene.getGeometryInstance(instanceID);
    if (instance.isDynamic())
    {
        uint prevVertexIndex = gScene.meshes[instance.geometryID].prevVbOffset + vIn.vertexID;
        prevPos = gScene.prevVertices[prevVertexIndex].position;
    }
    float3 prevPosW = mul(gScene.getPrevWorldMatrix(instanceID), float4(prevPos, 1.f)).xyz;
    vOut.prevPosH = mul(gShadowDepthPassData.shadowCamera.data.prevViewProjMatNoJitter, float4(prevPosW, 1.f));

    return vOut;
}

void psMain(VSOut vsOut, uint triangleIndex: SV_PrimitiveID) : SV_TARGET
{
#if USE_ALPHA_TEST
    let lod = ImplicitLodTextureSampler();
    if (alphaTest(vsOut, triangleIndex, lod))
        discard;
#endif
}
