# Copyright 2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Metrics calculation and analysis module.

Provides comprehensive analysis of PDF processing results including:
- Compression ratio calculations
- Performance metrics
- Token usage analysis
- Cost estimation
- Trend analysis

Requires:
    - pandas for data analysis
    - pathlib for file handling
    - datetime for timestamp handling

Ensures:
    - Accurate compression calculations
    - Comprehensive performance analysis
    - Cost-effective token usage tracking
    - Detailed reporting capabilities
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
import json

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

from src.pdf_processor import ProcessingMetrics


logger = logging.getLogger( __name__ )


@dataclass
class CostAnalysis:
    """
    Cost analysis for Gemini API usage.

    Attributes:
        total_tokens: Total tokens consumed
        estimated_cost_usd: Estimated cost in USD
        cost_per_file: Average cost per file
        cost_per_page: Average cost per page
        cost_per_image: Average cost per image
    """
    total_tokens: int
    estimated_cost_usd: float
    cost_per_file: float
    cost_per_page: float
    cost_per_image: float


@dataclass
class PerformanceAnalysis:
    """
    Performance analysis for processing efficiency.

    Attributes:
        avg_processing_time: Average processing time per file
        files_per_minute: Processing rate in files per minute
        pages_per_minute: Processing rate in pages per minute
        images_per_minute: Processing rate in images per minute
        bottleneck_analysis: Identified performance bottlenecks
    """
    avg_processing_time: float
    files_per_minute: float
    pages_per_minute: float
    images_per_minute: float
    bottleneck_analysis: str


@dataclass
class CompressionAnalysis:
    """
    Compression analysis for space efficiency.

    Attributes:
        avg_compression_ratio: Average compression achieved
        best_compression: Best compression ratio achieved
        worst_compression: Worst compression ratio achieved
        compression_by_file_size: Compression efficiency by file size
        space_saved_mb: Total space saved in MB
    """
    avg_compression_ratio: float
    best_compression: float
    worst_compression: float
    compression_by_file_size: Dict[str, float]  # size_range -> avg_compression
    space_saved_mb: float


class MetricsAnalyzer:
    """
    Comprehensive metrics analyzer for PDF processing results.

    Provides detailed analysis of processing efficiency, cost,
    and compression performance across multiple files.
    """

    # Gemini 2.5 Flash pricing (approximate - check current rates)
    GEMINI_FLASH_COST_PER_1K_TOKENS = 0.000075  # $0.075 per 1M tokens

    def __init__( self, debug: bool = False ):
        """
        Initialize metrics analyzer.

        Requires:
            - debug: Enable debug logging

        Ensures:
            - Analyzer is ready for metrics calculation
            - Proper logging configuration
        """
        self.debug = debug

        if debug:
            logger.setLevel( logging.DEBUG )
            logger.debug( "Metrics analyzer initialized" )


    def calculate_compression_ratio( self, original_size: int, compressed_size: int ) -> float:
        """
        Calculate compression ratio as percentage.

        Requires:
            - original_size: Original file size in bytes
            - compressed_size: Compressed content size in bytes

        Ensures:
            - Returns compression ratio as percentage (0-100)
            - Handles edge cases (zero sizes, larger compressed)

        Formula: (1 - compressed_size / original_size) * 100
        """
        if original_size == 0:
            return 0.0

        if compressed_size >= original_size:
            return 0.0  # No compression achieved

        ratio = ( 1 - compressed_size / original_size ) * 100
        return max( 0.0, min( 100.0, ratio ) )  # Clamp to 0-100


    def analyze_costs( self, results: List[Dict[str, Any]] ) -> CostAnalysis:
        """
        Analyze API costs for Gemini usage.

        Requires:
            - results: List of processing result dictionaries

        Ensures:
            - Returns comprehensive cost analysis
            - Includes per-file, per-page, and per-image costs
            - Uses current Gemini pricing estimates
        """
        if not results:
            return CostAnalysis( 0, 0.0, 0.0, 0.0, 0.0 )

        total_tokens = sum( r["metrics"].gemini_tokens_used for r in results )
        total_files = len( results )
        total_pages = sum( r["metrics"].pages_processed for r in results )
        total_images = sum( r["metrics"].images_found for r in results )

        # Calculate estimated cost
        estimated_cost = ( total_tokens / 1000 ) * self.GEMINI_FLASH_COST_PER_1K_TOKENS

        # Calculate per-unit costs
        cost_per_file = estimated_cost / total_files if total_files > 0 else 0.0
        cost_per_page = estimated_cost / total_pages if total_pages > 0 else 0.0
        cost_per_image = estimated_cost / total_images if total_images > 0 else 0.0

        return CostAnalysis(
            total_tokens=total_tokens,
            estimated_cost_usd=estimated_cost,
            cost_per_file=cost_per_file,
            cost_per_page=cost_per_page,
            cost_per_image=cost_per_image
        )


    def analyze_performance( self, results: List[Dict[str, Any]] ) -> PerformanceAnalysis:
        """
        Analyze processing performance metrics.

        Requires:
            - results: List of processing result dictionaries

        Ensures:
            - Returns comprehensive performance analysis
            - Includes processing rates and bottleneck identification
            - Provides actionable insights for optimization
        """
        if not results:
            return PerformanceAnalysis( 0.0, 0.0, 0.0, 0.0, "No data available" )

        total_time = sum( r["metrics"].processing_time_seconds for r in results )
        total_files = len( results )
        total_pages = sum( r["metrics"].pages_processed for r in results )
        total_images = sum( r["metrics"].images_found for r in results )

        # Calculate rates
        avg_processing_time = total_time / total_files if total_files > 0 else 0.0
        files_per_minute = ( total_files / total_time ) * 60 if total_time > 0 else 0.0
        pages_per_minute = ( total_pages / total_time ) * 60 if total_time > 0 else 0.0
        images_per_minute = ( total_images / total_time ) * 60 if total_time > 0 else 0.0

        # Bottleneck analysis
        avg_images_per_file = total_images / total_files if total_files > 0 else 0
        if avg_images_per_file > 20:
            bottleneck = "High image count - consider parallel processing"
        elif avg_processing_time > 60:
            bottleneck = "Long processing time - check network/API latency"
        elif images_per_minute < 10:
            bottleneck = "Slow image processing - optimize image sizes"
        else:
            bottleneck = "Performance appears optimal"

        return PerformanceAnalysis(
            avg_processing_time=avg_processing_time,
            files_per_minute=files_per_minute,
            pages_per_minute=pages_per_minute,
            images_per_minute=images_per_minute,
            bottleneck_analysis=bottleneck
        )


    def analyze_compression( self, results: List[Dict[str, Any]] ) -> CompressionAnalysis:
        """
        Analyze compression efficiency across files.

        Requires:
            - results: List of processing result dictionaries

        Ensures:
            - Returns comprehensive compression analysis
            - Includes efficiency by file size categories
            - Calculates total space savings
        """
        if not results:
            return CompressionAnalysis( 0.0, 0.0, 0.0, {}, 0.0 )

        compression_ratios = [ r["metrics"].compression_ratio for r in results ]

        avg_compression = sum( compression_ratios ) / len( compression_ratios )
        best_compression = max( compression_ratios )
        worst_compression = min( compression_ratios )

        # Calculate space saved
        total_original_mb = sum( r["metrics"].original_size_bytes for r in results ) / ( 1024 * 1024 )
        total_compressed_mb = sum( r["metrics"].full_extraction_bytes for r in results ) / ( 1024 * 1024 )
        space_saved_mb = total_original_mb - total_compressed_mb

        # Analyze compression by file size
        size_categories = {
            "small (< 5MB)": [],
            "medium (5-15MB)": [],
            "large (> 15MB)": []
        }

        for result in results:
            size_mb = result["metrics"].original_size_bytes / ( 1024 * 1024 )
            compression = result["metrics"].compression_ratio

            if size_mb < 5:
                size_categories["small (< 5MB)"].append( compression )
            elif size_mb < 15:
                size_categories["medium (5-15MB)"].append( compression )
            else:
                size_categories["large (> 15MB)"].append( compression )

        # Calculate averages by category
        compression_by_size = {}
        for category, ratios in size_categories.items():
            if ratios:
                compression_by_size[category] = sum( ratios ) / len( ratios )
            else:
                compression_by_size[category] = 0.0

        return CompressionAnalysis(
            avg_compression_ratio=avg_compression,
            best_compression=best_compression,
            worst_compression=worst_compression,
            compression_by_file_size=compression_by_size,
            space_saved_mb=space_saved_mb
        )


    def generate_comprehensive_report( self, results: List[Dict[str, Any]] ) -> Dict[str, Any]:
        """
        Generate comprehensive analysis report.

        Requires:
            - results: List of processing result dictionaries

        Ensures:
            - Returns complete analysis including all metrics
            - Suitable for JSON serialization
            - Includes recommendations and insights
        """
        if not results:
            return {
                "timestamp": datetime.now().isoformat(),
                "status": "no_data",
                "message": "No processing results available for analysis"
            }

        # Perform all analyses
        cost_analysis = self.analyze_costs( results )
        performance_analysis = self.analyze_performance( results )
        compression_analysis = self.analyze_compression( results )

        # Generate recommendations
        recommendations = []

        if cost_analysis.cost_per_file > 0.10:
            recommendations.append( "Consider batch processing to reduce per-file overhead" )

        if performance_analysis.images_per_minute < 10:
            recommendations.append( "Image processing is slow - consider resizing images before processing" )

        if compression_analysis.avg_compression_ratio < 90:
            recommendations.append( "Low compression ratio - PDFs may have mostly text content" )

        if not recommendations:
            recommendations.append( "Processing appears optimized - no immediate improvements needed" )

        # Compile comprehensive report
        report = {
            "timestamp": datetime.now().isoformat(),
            "status": "success",
            "files_analyzed": len( results ),
            "cost_analysis": asdict( cost_analysis ),
            "performance_analysis": asdict( performance_analysis ),
            "compression_analysis": asdict( compression_analysis ),
            "recommendations": recommendations,
            "summary": {
                "total_space_saved_mb": compression_analysis.space_saved_mb,
                "estimated_total_cost_usd": cost_analysis.estimated_cost_usd,
                "avg_processing_time_seconds": performance_analysis.avg_processing_time,
                "avg_compression_ratio": compression_analysis.avg_compression_ratio
            }
        }

        return report


    def save_analysis_report( self, results: List[Dict[str, Any]], output_path: Path ) -> None:
        """
        Save comprehensive analysis report to file.

        Requires:
            - results: List of processing result dictionaries
            - output_path: Path for analysis report file

        Ensures:
            - Creates detailed JSON analysis report
            - Includes all metrics and recommendations
            - Handles file writing errors gracefully
        """
        try:
            report = self.generate_comprehensive_report( results )

            with open( output_path, 'w', encoding='utf-8' ) as f:
                json.dump( report, f, indent=2, ensure_ascii=False )

            if self.debug:
                logger.debug( f"Analysis report saved to: {output_path}" )

        except Exception as e:
            logger.error( f"Failed to save analysis report: {e}" )
            raise


    def create_dataframe( self, results: List[Dict[str, Any]] ) -> Optional[object]:
        """
        Create pandas DataFrame for advanced analysis.

        Requires:
            - results: List of processing result dictionaries

        Ensures:
            - Returns pandas DataFrame if available
            - Handles missing pandas gracefully
            - Includes all relevant metrics columns
        """
        if not PANDAS_AVAILABLE:
            logger.warning( "Pandas not available - skipping DataFrame creation" )
            return None

        if not results:
            return None

        # Prepare data for DataFrame
        data = []
        for result in results:
            metrics = result["metrics"]
            row = {
                "filename": result["filename"],
                "original_size_mb": metrics.original_size_bytes / ( 1024 * 1024 ),
                "text_only_kb": metrics.text_only_bytes / 1024,
                "full_extraction_kb": metrics.full_extraction_bytes / 1024,
                "compression_ratio": metrics.compression_ratio,
                "pages": metrics.pages_processed,
                "images": metrics.images_found,
                "processing_time": metrics.processing_time_seconds,
                "tokens_used": metrics.gemini_tokens_used
            }
            data.append( row )

        df = pd.DataFrame( data )

        if self.debug:
            logger.debug( f"Created DataFrame with {len( df )} rows and {len( df.columns )} columns" )

        return df


if __name__ == "__main__":
    """Test the metrics analyzer when run directly."""
    import random

    # Create test data
    test_results = []
    for i in range( 5 ):
        test_results.append( {
            "filename": f"test_document_{i + 1}.pdf",
            "metrics": ProcessingMetrics(
                original_size_bytes=random.randint( 1000000, 20000000 ),
                text_only_bytes=random.randint( 50000, 200000 ),
                full_extraction_bytes=random.randint( 100000, 300000 ),
                compression_ratio=random.uniform( 85, 99 ),
                pages_processed=random.randint( 10, 100 ),
                images_found=random.randint( 5, 50 ),
                processing_time_seconds=random.uniform( 10, 120 ),
                gemini_tokens_used=random.randint( 5000, 25000 )
            )
        } )

    # Test analyzer
    analyzer = MetricsAnalyzer( debug=True )

    cost_analysis = analyzer.analyze_costs( test_results )
    performance_analysis = analyzer.analyze_performance( test_results )
    compression_analysis = analyzer.analyze_compression( test_results )

    print( f"✅ Metrics analyzer test completed" )
    print( f"   Average compression: {compression_analysis.avg_compression_ratio:.1f}%" )
    print( f"   Estimated cost: ${cost_analysis.estimated_cost_usd:.4f}" )
    print( f"   Processing rate: {performance_analysis.files_per_minute:.1f} files/min" )