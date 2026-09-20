// Small grazing-angle contribution gives the groom a soft fibre sheen.
// This is a realtime approximation, not full strand light scattering.
// API: Cesium 1.127 Documentation/CustomShaderGuide/README.md.
export function createFurLight(C) {
  return new C.CustomShader({
    mode: C.CustomShaderMode.MODIFY_MATERIAL,
    fragmentShaderText: `
      void fragmentMain(FragmentInput fsInput, inout czm_modelMaterial material) {
        if (material.roughness > 0.96) {
          vec3 normal = normalize(fsInput.attributes.normalEC);
          material.normalEC = normal;
          vec3 view = normalize(-fsInput.attributes.positionEC);
          float grazing = pow(1.0 - abs(dot(normal, view)), 3.0);
          material.emissive += material.diffuse * (0.025 + 0.13 * grazing);
        }
      }
    `,
  });
}
