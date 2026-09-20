// Small grazing-angle contribution gives the groom a soft fibre sheen.
// This is a realtime approximation, not full strand light scattering.
// API: Cesium 1.127 Documentation/CustomShaderGuide/README.md.
export function createFurLight(C) {
  return new C.CustomShader({
    mode: C.CustomShaderMode.MODIFY_MATERIAL,
    fragmentShaderText: `
      void fragmentMain(FragmentInput fsInput, inout czm_modelMaterial material) {
        if (material.roughness < 0.16) {
          vec3 eyeNormal = normalize(fsInput.attributes.normalEC);
          vec3 eyeView = normalize(-fsInput.attributes.positionEC);
          vec3 reflection = reflect(-eyeView, eyeNormal);
          vec3 worldPosition = (czm_inverseView * vec4(fsInput.attributes.positionEC, 1.0)).xyz;
          vec3 skyUp = normalize(czm_viewRotation * normalize(worldPosition));
          float fresnel = 0.025 + 0.975 * pow(1.0 - max(dot(eyeNormal, eyeView), 0.0), 5.0);
          float sky = smoothstep(-0.25, 0.6, dot(reflection, skyUp));
          vec3 environment = mix(vec3(0.05, 0.065, 0.045), vec3(0.58, 0.72, 0.86), sky);
          float sun = pow(max(dot(reflection, normalize(czm_sunDirectionEC)), 0.0), 220.0);
          // Broad sky reflection plus a small curved sun highlight; no white spheres.
          material.emissive += material.diffuse * 0.20 + environment * (0.015 + fresnel * 0.22) + vec3(0.85, 0.81, 0.72) * sun;
          material.specular = vec3(0.025);
          material.roughness = 0.085;
        }
        if (material.roughness > 0.85 && material.roughness < 0.96) {
          material.emissive += material.diffuse * 0.12;
        }
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
