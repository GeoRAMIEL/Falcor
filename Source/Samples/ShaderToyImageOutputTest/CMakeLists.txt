add_falcor_executable(ShaderToyImageOutputTest)

target_sources(ShaderToyImageOutputTest PRIVATE
    ShaderToyImageOutputTest.cpp
    ShaderToyImageOutputTest.h
    Toy.ps.slang
)

target_copy_shaders(ShaderToyImageOutputTest Samples/ShaderToyImageOutputTest)

target_source_group(ShaderToyImageOutputTest "Samples")
