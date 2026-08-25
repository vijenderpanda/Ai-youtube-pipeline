#!/usr/bin/env python3
"""
person_cut.py — fast host cutouts via Apple Vision person segmentation (GPU).
Replaces rembg for video (rembg = ~11s/frame CPU; Vision = ~10 fps+).

Usage: python3 person_cut.py <in_dir_of_pngs> <out_dir>
Needs pyobjc (Vision/Quartz) — system python3 or any env with pyobjc.
"""
import os, sys

import Quartz  # noqa
import Vision
from Cocoa import NSURL
from Quartz import (CGImageDestinationCreateWithURL, CGImageDestinationAddImage,
                    CGImageDestinationFinalize, CIImage, CIContext, CIFilter)
import objc


def main(fin, fout):
    os.makedirs(fout, exist_ok=True)
    ctx = CIContext.context()
    files = sorted(f for f in os.listdir(fin) if f.endswith(".png"))
    req = Vision.VNGeneratePersonSegmentationRequest.alloc().initWithCompletionHandler_(None)
    req.setQualityLevel_(Vision.VNGeneratePersonSegmentationRequestQualityLevelAccurate)
    req.setOutputPixelFormat_(Quartz.kCVPixelFormatType_OneComponent8)
    for i, f in enumerate(files):
        url = NSURL.fileURLWithPath_(os.path.join(fin, f))
        src = CIImage.imageWithContentsOfURL_(url)
        handler = Vision.VNImageRequestHandler.alloc().initWithCIImage_options_(src, None)
        ok, err = handler.performRequests_error_([req], None)
        if not ok:
            raise RuntimeError(f"Vision failed on {f}: {err}")
        pb = req.results()[0].pixelBuffer()
        mask = CIImage.imageWithCVPixelBuffer_(pb)
        sx = src.extent().size.width / mask.extent().size.width
        sy = src.extent().size.height / mask.extent().size.height
        mask = mask.imageByApplyingTransform_(
            Quartz.CGAffineTransformMakeScale(sx, sy))
        blend = CIFilter.filterWithName_("CIBlendWithMask")
        blend.setValue_forKey_(src, "inputImage")
        blend.setValue_forKey_(mask, "inputMaskImage")
        outimg = blend.valueForKey_("outputImage")
        cg = ctx.createCGImage_fromRect_(outimg, src.extent())
        durl = NSURL.fileURLWithPath_(os.path.join(fout, f))
        dest = CGImageDestinationCreateWithURL(durl, "public.png", 1, None)
        CGImageDestinationAddImage(dest, cg, None)
        CGImageDestinationFinalize(dest)
        if i % 100 == 0:
            print(f"{i}/{len(files)}", flush=True)
    print(f"done {len(files)}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
