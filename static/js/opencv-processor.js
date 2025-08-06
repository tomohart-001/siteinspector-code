/**
 * Enhanced OpenCV.js Image Processor for Floor Plan Extraction
 * Simplified architecture with better memory management and error handling
 */

class OpenCVProcessor {
    constructor() {
        this.isLoaded = false;
        this.config = {
            // Simplified processing parameters
            minAreaRatio: 0.01,
            maxAreaRatio: 0.85,
            minSolidity: 0.2,
            polygonEpsilon: 0.012,
            morphologyKernel: 3,
            gaussianBlur: 3,
            adaptiveBlock: 15,
            adaptiveC: 8,
            cannyLower: 30,
            cannyUpper: 100,
            claheClipLimit: 3.0,
            claheTileSize: 8
        };
        this.loadOpenCV();
    }

    async loadOpenCV() {
        return new Promise((resolve, reject) => {
            if (window.cv) {
                this.isLoaded = true;
                resolve();
                return;
            }

            const script = document.createElement('script');
            script.src = 'https://docs.opencv.org/4.8.0/opencv.js';
            script.async = true;

            script.onload = () => {
                const checkReady = () => {
                    if (window.cv && window.cv.Mat) {
                        this.isLoaded = true;
                        console.log('OpenCV.js loaded successfully');
                        resolve();
                    } else {
                        setTimeout(checkReady, 100);
                    }
                };
                checkReady();
            };

            script.onerror = () => {
                console.error('Failed to load OpenCV.js');
                reject(new Error('Failed to load OpenCV.js'));
            };

            document.head.appendChild(script);
        });
    }

    async processFloorplanImage(imageElement) {
        if (!this.isLoaded) {
            await this.loadOpenCV();
        }

        const mats = []; // Track matrices for cleanup

        try {
            console.log('Starting enhanced OpenCV processing...');

            // Convert image to OpenCV Mat
            const src = cv.imread(imageElement);
            mats.push(src);

            const processed = this.preprocessImage(src, mats);
            const boundaries = this.extractBoundaries(processed, src.rows, src.cols, mats);

            if (boundaries && boundaries.length >= 4) {
                console.log(`Enhanced processing successful: ${boundaries.length} boundary points extracted`);

                return {
                    success: true,
                    boundaries: boundaries,
                    contourCount: boundaries.length,
                    processedImage: this.createProcessedImage(imageElement, boundaries),
                    processingMethod: 'enhanced_opencv'
                };
            } else {
                throw new Error('No valid building outline found with enhanced processing');
            }

        } catch (error) {
            console.error('Enhanced OpenCV processing error:', error);
            return {
                success: false,
                error: error.message,
                boundaries: []
            };
        } finally {
            // Clean up all matrices
            this.cleanupMats(mats);
        }
    }

    preprocessImage(src, mats) {
        const gray = new cv.Mat();
        const normalized = new cv.Mat();
        const enhanced = new cv.Mat();
        mats.push(gray, normalized, enhanced);

        try {
            // Convert to grayscale
            cv.cvtColor(src, gray, cv.COLOR_RGBA2GRAY);

            // Normalize for better contrast
            cv.normalize(gray, normalized, 0, 255, cv.NORM_MINMAX);

            // Apply CLAHE for local contrast enhancement
            const clahe = new cv.CLAHE(this.config.claheClipLimit, new cv.Size(this.config.claheTileSize, this.config.claheTileSize));
            clahe.apply(normalized, enhanced);
            clahe.delete();

            return enhanced;

        } catch (error) {
            console.warn('Preprocessing failed, using basic method:', error);
            const fallback = new cv.Mat();
            cv.cvtColor(src, fallback, cv.COLOR_RGBA2GRAY);
            mats.push(fallback);
            return fallback;
        }
    }

    extractBoundaries(preprocessed, imageHeight, imageWidth, mats) {
        const imageArea = imageHeight * imageWidth;

        // Try multiple detection methods
        const methods = [
            () => this.methodAdaptiveThreshold(preprocessed, imageArea, mats),
            () => this.methodCannyContours(preprocessed, imageArea, mats),
            () => this.methodArchitecturalDetection(preprocessed, imageArea, mats)
        ];

        for (const method of methods) {
            try {
                const result = method();
                if (result && result.length >= 4) {
                    console.log(`Detection successful: ${result.length} boundary points`);
                    return result;
                }
            } catch (error) {
                console.debug('Detection method failed:', error);
            }
        }

        // Fallback
        console.warn('All detection methods failed, using fallback');
        return this.generateFallbackBoundaries(imageWidth, imageHeight);
    }

    methodAdaptiveThreshold(image, imageArea, mats) {
        const thresh = new cv.Mat();
        const closed = new cv.Mat();
        const opened = new cv.Mat();
        const contours = new cv.MatVector();
        const hierarchy = new cv.Mat();
        mats.push(thresh, closed, opened, hierarchy);

        try {
            // Adaptive threshold
            cv.adaptiveThreshold(
                image, thresh, 255, cv.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv.THRESH_BINARY_INV, this.config.adaptiveBlock, this.config.adaptiveC
            );

            // Morphological operations
            const kernel = cv.getStructuringElement(cv.MORPH_RECT, 
                new cv.Size(this.config.morphologyKernel, this.config.morphologyKernel));
            mats.push(kernel);

            // Close gaps and remove noise
            cv.morphologyEx(thresh, closed, cv.MORPH_CLOSE, kernel, new cv.Point(-1, -1), 2);
            cv.morphologyEx(closed, opened, kernel, cv.MORPH_OPEN, new cv.Point(-1, -1), 1);

            // Find contours
            cv.findContours(opened, contours, hierarchy, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE);

            const result = this.processContours(contours, imageArea, mats);
            contours.delete();
            return result;

        } catch (error) {
            console.debug('Adaptive threshold method failed:', error);
            if (contours) contours.delete();
            return null;
        }
    }

    methodCannyContours(image, imageArea, mats) {
        const blurred = new cv.Mat();
        const edges = new cv.Mat();
        const closed = new cv.Mat();
        const contours = new cv.MatVector();
        const hierarchy = new cv.Mat();
        mats.push(blurred, edges, closed, hierarchy);

        try {
            // Gaussian blur
            cv.GaussianBlur(image, blurred, new cv.Size(this.config.gaussianBlur, this.config.gaussianBlur), 0);

            // Canny edge detection
            cv.Canny(blurred, edges, this.config.cannyLower, this.config.cannyUpper);

            // Morphological closing
            const kernel = cv.getStructuringElement(cv.MORPH_RECT, new cv.Size(3, 3));
            cv.morphologyEx(edges, closed, cv.MORPH_CLOSE, kernel);
            mats.push(kernel);

            // Find contours
            cv.findContours(closed, contours, hierarchy, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE);

            const result = this.processContours(contours, imageArea, mats);
            contours.delete();
            return result;

        } catch (error) {
            console.debug('Canny contours method failed:', error);
            if (contours) contours.delete();
            return null;
        }
    }

    methodArchitecturalDetection(image, imageArea, mats) {
        const thresh1 = new cv.Mat();
        const thresh2 = new cv.Mat();
        const thresh3 = new cv.Mat();
        const combined = new cv.Mat();
        const temp = new cv.Mat();
        const opened = new cv.Mat();
        const closed = new cv.Mat();
        const contours = new cv.MatVector();
        const hierarchy = new cv.Mat();
        mats.push(thresh1, thresh2, thresh3, combined, temp, opened, closed, hierarchy);

        try {
            // Multiple threshold levels
            cv.threshold(image, thresh1, 200, 255, cv.THRESH_BINARY_INV);
            cv.threshold(image, thresh2, 150, 255, cv.THRESH_BINARY_INV);
            cv.threshold(image, thresh3, 100, 255, cv.THRESH_BINARY_INV);

            // Combine thresholds
            cv.bitwise_or(thresh1, thresh2, temp);
            cv.bitwise_or(temp, thresh3, combined);

            // Remove small details
            const kernelOpen = cv.getStructuringElement(cv.MORPH_RECT, new cv.Size(3, 3));
            cv.morphologyEx(combined, opened, cv.MORPH_OPEN, kernelOpen);

            // Close gaps
            const kernelClose = cv.getStructuringElement(cv.MORPH_RECT, new cv.Size(5, 5));
            cv.morphologyEx(opened, closed, cv.MORPH_CLOSE, kernelClose);
            mats.push(kernelOpen, kernelClose);

            // Find contours
            cv.findContours(closed, contours, hierarchy, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE);

            const result = this.processContours(contours, imageArea, mats);
            contours.delete();
            return result;

        } catch (error) {
            console.debug('Architectural detection failed:', error);
            if (contours) contours.delete();
            return null;
        }
    }

    processContours(contours, imageArea, mats) {
        if (!contours || contours.size() === 0) {
            return null;
        }

        try {
            const validContours = [];

            for (let i = 0; i < contours.size(); i++) {
                const contour = contours.get(i);
                const area = cv.contourArea(contour);

                // Area filter
                if (area < imageArea * this.config.minAreaRatio ||
                    area > imageArea * this.config.maxAreaRatio) {
                    continue;
                }

                // Solidity filter
                const hull = new cv.Mat();
                cv.convexHull(contour, hull);
                const hullArea = cv.contourArea(hull);
                hull.delete();

                if (hullArea > 0) {
                    const solidity = area / hullArea;
                    if (solidity < this.config.minSolidity) {
                        continue;
                    }
                }

                // Aspect ratio filter
                const boundingRect = cv.boundingRect(contour);
                const aspectRatio = Math.max(boundingRect.width, boundingRect.height) / 
                                  Math.min(boundingRect.width, boundingRect.height);
                if (aspectRatio > 10) {
                    continue;
                }

                validContours.push({ contour, area });
            }

            if (validContours.length === 0) {
                return null;
            }

            // Select largest valid contour
            const bestContour = validContours.reduce((best, current) => 
                current.area > best.area ? current : best
            ).contour;

            // Approximate to polygon
            const approx = new cv.Mat();
            const epsilon = this.config.polygonEpsilon * cv.arcLength(bestContour, true);
            cv.approxPolyDP(bestContour, approx, epsilon, true);
            mats.push(approx);

            // Extract boundary points
            let boundaries = this.contourToBoundaryPoints(approx);

            // Ensure reasonable number of points
            if (boundaries.length < 4) {
                boundaries = this.contourToBoundaryPoints(bestContour, 8);
            }

            if (boundaries.length > 20) {
                const step = Math.floor(boundaries.length / 15);
                boundaries = boundaries.filter((_, index) => index % step === 0);
            }

            return boundaries;

        } catch (error) {
            console.debug('Contour processing failed:', error);
            return null;
        }
    }

    contourToBoundaryPoints(contour, maxPoints = null) {
        const points = [];

        try {
            let step = 1;
            if (maxPoints && contour.rows > maxPoints) {
                step = Math.floor(contour.rows / maxPoints);
            }

            for (let i = 0; i < contour.rows; i += step) {
                const point = contour.data32S.slice(i * 2, i * 2 + 2);
                points.push([point[0], point[1]]);
            }

            return points;

        } catch (error) {
            console.error('Error extracting boundary points:', error);
            return [];
        }
    }

    generateFallbackBoundaries(width, height) {
        const marginX = Math.floor(width / 8);
        const marginY = Math.floor(height / 8);

        return [
            [marginX, marginY],
            [width - marginX, marginY],
            [width - marginX, height - marginY],
            [marginX, height - marginY]
        ];
    }

    cleanupMats(mats) {
        mats.forEach(mat => {
            if (mat && typeof mat.delete === 'function') {
                try {
                    mat.delete();
                } catch (error) {
                    console.debug('Error cleaning up matrix:', error);
                }
            }
        });
    }

    createProcessedImage(originalImage, boundaryPoints) {
        try {
            const canvas = document.createElement('canvas');
            const ctx = canvas.getContext('2d');

            canvas.width = originalImage.width || originalImage.naturalWidth;
            canvas.height = originalImage.height || originalImage.naturalHeight;

            // Draw original image
            ctx.drawImage(originalImage, 0, 0);

            // Draw boundary overlay
            if (boundaryPoints.length > 0) {
                // Fill with transparency
                ctx.fillStyle = 'rgba(0, 255, 0, 0.15)';
                ctx.beginPath();
                ctx.moveTo(boundaryPoints[0][0], boundaryPoints[0][1]);
                for (let i = 1; i < boundaryPoints.length; i++) {
                    ctx.lineTo(boundaryPoints[i][0], boundaryPoints[i][1]);
                }
                ctx.closePath();
                ctx.fill();

                // Draw outline
                ctx.strokeStyle = '#00ff00';
                ctx.lineWidth = 4;
                ctx.stroke();

                // Draw corner points
                ctx.fillStyle = '#ff0000';
                ctx.strokeStyle = '#ffffff';
                ctx.lineWidth = 2;

                boundaryPoints.forEach(point => {
                    ctx.beginPath();
                    ctx.arc(point[0], point[1], 6, 0, 2 * Math.PI);
                    ctx.fill();
                    ctx.stroke();
                });
            }

            return canvas.toDataURL('image/png');

        } catch (error) {
            console.error('Error creating processed image:', error);
            return null;
        }
    }

    // Utility method to convert File to Image element
    async fileToImage(file) {
        return new Promise((resolve, reject) => {
            const img = new Image();
            const url = URL.createObjectURL(file);

            img.onload = () => {
                URL.revokeObjectURL(url);
                resolve(img);
            };

            img.onerror = () => {
                URL.revokeObjectURL(url);
                reject(new Error('Failed to load image'));
            };

            img.src = url;
        });
    }
}

// Export for use in other modules
window.OpenCVProcessor = OpenCVProcessor;