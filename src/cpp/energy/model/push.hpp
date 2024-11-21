// File: push.hpp
// Author: Ryoichi Ando (ryoichi.ando@zozo.com)
// License: Apache v2.0

#ifndef PUSH_HPP
#define PUSH_HPP

#include "../../common.hpp"
#include "../../data.hpp"

namespace push {

__device__ float sqr(float x) { return x * x; }
__device__ float cube(float x) { return x * x * x; }

__device__ float energy(const Vec3f &x, const Vec3f &y, const Vec3f &normal,
                        float eps) {
    Vec3f e = x - y;
    float d = e.dot(normal);
    if (d < 0.0f) {
        return -cube(d) / (3.0f * eps);
    } else {
        return 0.0f;
    }
}

__device__ Vec3f gradient(const Vec3f &x, const Vec3f &y, const Vec3f &normal,
                          float eps) {
    Vec3f e = x - y;
    float d = e.dot(normal);
    if (d < 0.0f) {
        return -sqr(d) / eps * normal;
    } else {
        return Vec3f::Zero();
    }
}

__device__ float curvature(const Vec3f &x, const Vec3f &y, const Vec3f &normal,
                           float eps) {
    Vec3f e = x - y;
    float d = e.dot(normal);
    if (d < 0.0f) {
        return -2.0f * d / eps;
    } else {
        return 0.0f;
    }
}

__device__ Mat3x3f hessian(const Vec3f &x, const Vec3f &y, const Vec3f &normal,
                           float eps) {
    return curvature(x, y, normal, eps) * normal * normal.transpose();
}

} // namespace push

#endif
