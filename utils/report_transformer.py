"""
Report Transformation Engine for HVLC_DB

This module provides tools for transforming various report formats into
a canonical format for database storage and processing.
"""

import os
import json
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Set, Any, Callable
from datetime import datetime
import re
import logging
from pathlib import Path

from utils.config import get_config
from utils.logger import get_logger, log_data_quality_issue
from utils.format_detector import ReportFormatDetector, FormatDetectionResult

# Configure logging
logger = get_logger()
config = get_config()


class TransformationRule:
    """Base class for transformation rules"""
    
    def __init__(self, name: str, description: str = None):
        """Initialize transformation rule
        
        Args:
            name: Rule name
            description: Rule description
        """
        self.name = name
        self.description = description or f"Transformation rule for {name}"
        
    def apply(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply transformation rule to dataframe
        
        Args:
            df: Input dataframe
            
        Returns:
            Transformed dataframe
        """
        raise NotImplementedError("Subclasses must implement this method")


class RenameColumnsRule(TransformationRule):
    """Rule for renaming columns"""
    
    def __init__(self, column_map: Dict[str, str], name: str = "rename_columns"):
        """Initialize rule
        
        Args:
            column_map: Mapping of source columns to target columns
            name: Rule name
        """
        super().__init__(name, f"Rename columns according to mapping")
        self.column_map = column_map
        
    def apply(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply transformation
        
        Args:
            df: Input dataframe
            
        Returns:
            Dataframe with renamed columns
        """
        # Only rename columns that exist in the dataframe
        rename_map = {col: target for col, target in self.column_map.items() 
                     if col in df.columns}
        
        if not rename_map:
            logger.warning(f"No columns matched for renaming rule {self.name}")
            return df
            
        return df.rename(columns=rename_map)


class DateFormatRule(TransformationRule):
    """Rule for standardizing date formats"""
    
    def __init__(self, columns: List[str], 
                 input_formats: List[str] = None,
                 output_format: str = "%Y-%m-%d",
                 name: str = "standardize_dates"):
        """Initialize rule
        
        Args:
            columns: Date columns to standardize
            input_formats: List of input date formats to try
            output_format: Target date format
            name: Rule name
        """
        super().__init__(name, f"Standardize date formats in columns: {', '.join(columns)}")
        self.columns = columns
        self.input_formats = input_formats or [
            "%m/%d/%y", "%m/%d/%Y", "%m-%d-%Y", "%m-%d-%y", 
            "%Y-%m-%d", "%Y/%m/%d", "%d-%m-%Y", "%d/%m/%Y"
        ]
        self.output_format = output_format
        
    def apply(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply transformation
        
        Args:
            df: Input dataframe
            
        Returns:
            Dataframe with standardized date columns
        """
        result_df = df.copy()
        
        for column in self.columns:
            if column not in result_df.columns:
                logger.warning(f"Column {column} not found for date formatting")
                continue
                
            # Skip columns that are already datetime
            if pd.api.types.is_datetime64_any_dtype(result_df[column]):
                continue
                
            # Try to parse dates
            try:
                # First try pandas auto-detection
                result_df[column] = pd.to_datetime(
                    result_df[column], errors='coerce', infer_datetime_format=True
                )
                
                # For values that failed, try explicit formats
                mask = result_df[column].isna() & df[column].notna()
                if mask.any():
                    for date_format in self.input_formats:
                        try:
                            parsed_dates = pd.to_datetime(
                                df.loc[mask, column], format=date_format, errors='coerce'
                            )
                            # Update only previously failed values that parsed successfully
                            update_mask = mask & parsed_dates.notna()
                            result_df.loc[update_mask, column] = parsed_dates
                            mask = result_df[column].isna() & df[column].notna()
                            if not mask.any():
                                break
                        except Exception:
                            continue
                
                # Convert to target format
                result_df[column] = result_df[column].dt.strftime(self.output_format)
                
                # Log any remaining parsing failures
                failures = (result_df[column].isna() & df[column].notna()).sum()
                if failures > 0:
                    logger.warning(f"Failed to parse {failures} date values in column {column}")
                    
            except Exception as e:
                logger.error(f"Error formatting dates in column {column}: {e}")
                
        return result_df


class NumberFormatRule(TransformationRule):
    """Rule for standardizing number formats"""
    
    def __init__(self, columns: List[str], name: str = "standardize_numbers"):
        """Initialize rule
        
        Args:
            columns: Number columns to standardize
            name: Rule name
        """
        super().__init__(name, f"Standardize number formats in columns: {', '.join(columns)}")
        self.columns = columns
        
    def apply(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply transformation
        
        Args:
            df: Input dataframe
            
        Returns:
            Dataframe with standardized number columns
        """
        result_df = df.copy()
        
        for column in self.columns:
            if column not in result_df.columns:
                logger.warning(f"Column {column} not found for number formatting")
                continue
                
            # Skip columns that are already numeric
            if pd.api.types.is_numeric_dtype(result_df[column]):
                continue
                
            # Try to convert to numeric
            try:
                # Remove currency symbols and other characters
                if result_df[column].dtype == object:
                    result_df[column] = result_df[column].astype(str).str.replace(
                        r'[$,()%]', '', regex=True
                    )
                    
                result_df[column] = pd.to_numeric(result_df[column], errors='coerce')
                
                # Log any parsing failures
                failures = (result_df[column].isna() & df[column].notna()).sum()
                if failures > 0:
                    logger.warning(f"Failed to parse {failures} numeric values in column {column}")
                    
            except Exception as e:
                logger.error(f"Error formatting numbers in column {column}: {e}")
                
        return result_df


class MergeColumnsRule(TransformationRule):
    """Rule for merging multiple columns into one"""
    
    def __init__(self, source_columns: List[str], target_column: str, 
                 merge_func: Callable = None, name: str = "merge_columns"):
        """Initialize rule
        
        Args:
            source_columns: Columns to merge
            target_column: Target column name
            merge_func: Function to merge columns, receives series of columns and returns single value
            name: Rule name
        """
        super().__init__(
            name, 
            f"Merge columns {', '.join(source_columns)} into {target_column}"
        )
        self.source_columns = source_columns
        self.target_column = target_column
        self.merge_func = merge_func or self._default_merge
        
    def _default_merge(self, row):
        """Default merge function - take first non-null value"""
        for col in self.source_columns:
            if pd.notna(row[col]):
                return row[col]
        return None
        
    def apply(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply transformation
        
        Args:
            df: Input dataframe
            
        Returns:
            Dataframe with merged columns
        """
        result_df = df.copy()
        
        # Check if source columns exist
        existing_columns = [col for col in self.source_columns if col in result_df.columns]
        if not existing_columns:
            logger.warning(f"No source columns found for merge rule {self.name}")
            return result_df
            
        try:
            # Apply merge function
            result_df[self.target_column] = result_df.apply(self.merge_func, axis=1)
        except Exception as e:
            logger.error(f"Error merging columns in rule {self.name}: {e}")
            
        return result_df


class SplitColumnRule(TransformationRule):
    """Rule for splitting a column into multiple columns"""
    
    def __init__(self, source_column: str, target_columns: List[str], 
                 pattern: str, name: str = "split_column"):
        """Initialize rule
        
        Args:
            source_column: Column to split
            target_columns: Target column names
            pattern: Regex pattern for splitting
            name: Rule name
        """
        super().__init__(
            name, 
            f"Split column {source_column} into {', '.join(target_columns)}"
        )
        self.source_column = source_column
        self.target_columns = target_columns
        self.pattern = pattern
        
    def apply(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply transformation
        
        Args:
            df: Input dataframe
            
        Returns:
            Dataframe with split columns
        """
        result_df = df.copy()
        
        if self.source_column not in result_df.columns:
            logger.warning(f"Source column {self.source_column} not found for split rule {self.name}")
            return result_df
            
        try:
            # Extract values using regex
            split_df = result_df[self.source_column].str.extract(self.pattern)
            
            # Add extracted columns
            for i, col in enumerate(self.target_columns):
                if i < len(split_df.columns):
                    result_df[col] = split_df[i]
                    
        except Exception as e:
            logger.error(f"Error splitting column in rule {self.name}: {e}")
            
        return result_df


class AddConstantRule(TransformationRule):
    """Rule for adding a constant value column"""
    
    def __init__(self, column: str, value: Any, name: str = "add_constant"):
        """Initialize rule
        
        Args:
            column: Column to add
            value: Constant value
            name: Rule name
        """
        super().__init__(name, f"Add constant column {column} with value '{value}'")
        self.column = column
        self.value = value
        
    def apply(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply transformation
        
        Args:
            df: Input dataframe
            
        Returns:
            Dataframe with added column
        """
        result_df = df.copy()
        result_df[self.column] = self.value
        return result_df


class ForwardFillRule(TransformationRule):
    """Rule for forward-filling missing values in specified columns"""
    
    def __init__(self, columns: List[str], name: str = "forward_fill"):
        """Initialize rule
        
        Args:
            columns: Columns to forward-fill
            name: Rule name
        """
        super().__init__(name, f"Forward-fill missing values in columns: {', '.join(columns)}")
        self.columns = columns
        
    def apply(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply transformation
        
        Args:
            df: Input dataframe
            
        Returns:
            Dataframe with forward-filled values
        """
        result_df = df.copy()
        
        for column in self.columns:
            if column in result_df.columns:
                result_df[column] = result_df[column].fillna(method='ffill')
                
        return result_df


class ReportTransformer:
    """Transforms CSV reports into canonical format"""
    
    def __init__(self, format_detector: ReportFormatDetector = None):
        """Initialize report transformer
        
        Args:
            format_detector: ReportFormatDetector instance
        """
        self.format_detector = format_detector or ReportFormatDetector()
        self.canonical_columns = [
            "transaction_id", "transaction_date", "patient_id", "provider_id", 
            "provider_name", "cash_applied", "insurance_payment", "patient_payment", 
            "adjustment_amount", "payer_name", "payment_type", "claim_number",
            "cpt_code", "diagnosis_code", "service_date", "notes"
        ]
        self.transformation_pipelines = self._initialize_pipelines()
        
    def _initialize_pipelines(self) -> Dict[str, List[TransformationRule]]:
        """Initialize transformation pipelines for known formats
        
        Returns:
            Dictionary of format name to list of transformation rules
        """
        pipelines = {}
        
        # Credit Card Payment format pipeline
        cc_pipeline = [
            RenameColumnsRule({
                "Trans. #": "transaction_id",
                "Trans. Date": "transaction_date",
                "Gross Amt": "cash_applied",
                "Acct Type": "payment_type",
                "Client Name": "patient_id",
                "Provider": "provider_name"
            }),
            DateFormatRule(["transaction_date"]),
            NumberFormatRule(["cash_applied"]),
            AddConstantRule("payment_type", "credit_card")
        ]
        pipelines["credit_card_payment"] = cc_pipeline
        
        # Insurance Claims format pipeline
        insurance_pipeline = [
            RenameColumnsRule({
                "RowId": "transaction_id",
                "Check Date": "transaction_date",
                "Check Amount": "insurance_payment",
                "Cash Applied": "cash_applied",
                "Payment From": "payer_name",
                "Provider": "provider_name"
            }),
            DateFormatRule(["transaction_date"]),
            NumberFormatRule(["cash_applied", "insurance_payment"]),
            MergeColumnsRule(
                ["insurance_payment", "cash_applied"], 
                "cash_applied",
                lambda row: row["cash_applied"] if pd.notna(row["cash_applied"]) else row["insurance_payment"]
            ),
            AddConstantRule("payment_type", "insurance")
        ]
        pipelines["insurance_claims"] = insurance_pipeline
        
        # Hendersonville Payments format pipeline
        hendersonville_pipeline = [
            RenameColumnsRule({
                "Check Date": "transaction_date",
                "Date Posted": "posted_date",
                "Check Number": "check_number",
                "Payment From": "payer_name",
                "Reference": "reference",
                "Check Amount": "check_amount",
                "Cash Applied": "cash_applied",
                "Provider": "provider_name"
            }),
            DateFormatRule(["transaction_date", "posted_date"]),
            NumberFormatRule(["check_amount", "cash_applied"]),
            # Handle continuation rows by forward-filling dates and amounts
            ForwardFillRule(["transaction_date", "posted_date", "check_number", "payer_name", "provider_name", "check_amount"]),
            # Use check_amount as cash_applied when cash_applied is empty
            MergeColumnsRule(
                ["check_amount", "cash_applied"], 
                "cash_applied",
                lambda row: row["cash_applied"] if pd.notna(row["cash_applied"]) else row["check_amount"]
            ),
            AddConstantRule("payment_type", "insurance")
        ]
        pipelines["hendersonville_payments"] = hendersonville_pipeline
        
        return pipelines
        
    def transform(self, file_path: str, format_name: str = None) -> Tuple[pd.DataFrame, Dict]:
        """Transform a CSV file to canonical format
        
        Args:
            file_path: Path to CSV file
            format_name: Optional format name (detected if not provided)
            
        Returns:
            Tuple of (transformed dataframe, transformation metadata)
        """
        logger.info(f"Transforming file {file_path}")
        
        # Detect format if not provided
        if not format_name:
            detection_result = self.format_detector.detect_format(file_path)
            format_name = detection_result.format_name
            
            if not format_name:
                error_msg = "Could not detect file format"
                logger.error(error_msg)
                return pd.DataFrame(), {"error": error_msg}
                
            logger.info(f"Detected format: {format_name} (confidence: {detection_result.confidence:.2f})")
            
        # Check if we have a pipeline for this format
        if format_name not in self.transformation_pipelines:
            error_msg = f"No transformation pipeline defined for format {format_name}"
            logger.error(error_msg)
            return pd.DataFrame(), {"error": error_msg}
            
        try:
            # Read the file
            df = pd.read_csv(file_path)
            
            # Apply transformation pipeline
            pipeline = self.transformation_pipelines[format_name]
            transformation_log = []
            
            for rule in pipeline:
                before_shape = df.shape
                df = rule.apply(df)
                after_shape = df.shape
                
                # Log transformation
                transformation_log.append({
                    "rule": rule.name,
                    "description": rule.description,
                    "before_shape": before_shape,
                    "after_shape": after_shape
                })
                
            # Ensure all canonical columns exist (fill with NaN if missing)
            for column in self.canonical_columns:
                if column not in df.columns:
                    df[column] = np.nan
                    
            # Reorder columns to match canonical format
            df = df[self.canonical_columns]
            
            # Validate transformation
            validation_errors = self._validate_transformation(df, format_name)
            
            return df, {
                "format": format_name,
                "file_path": file_path,
                "transformation_log": transformation_log,
                "validation_errors": validation_errors,
                "success": len(validation_errors) == 0
            }
            
        except Exception as e:
            logger.error(f"Error transforming file {file_path}: {e}")
            return pd.DataFrame(), {"error": str(e)}
            
    def _validate_transformation(self, df: pd.DataFrame, format_name: str) -> List[Dict]:
        """Validate transformed data
        
        Args:
            df: Transformed dataframe
            format_name: Format name
            
        Returns:
            List of validation errors
        """
        errors = []
        
        # Check for missing required values
        required_columns = ["transaction_date", "cash_applied", "provider_name"]
        for column in required_columns:
            missing = df[column].isna().sum()
            if missing > 0:
                errors.append({
                    "type": "missing_required",
                    "column": column,
                    "count": missing,
                    "message": f"Missing {missing} values in required column {column}"
                })
                
        # Check for negative cash values
        if "cash_applied" in df.columns:
            negative = (df["cash_applied"] < 0).sum()
            if negative > 0:
                errors.append({
                    "type": "negative_values",
                    "column": "cash_applied",
                    "count": negative,
                    "message": f"Found {negative} negative values in cash_applied column"
                })
                
        # Check for date format issues
        date_columns = ["transaction_date", "service_date"]
        for column in date_columns:
            if column in df.columns and not pd.api.types.is_datetime64_any_dtype(df[column]):
                try:
                    pd.to_datetime(df[column], errors='raise')
                except Exception as e:
                    errors.append({
                        "type": "date_format",
                        "column": column,
                        "message": f"Date format issues in {column}: {str(e)}"
                    })
                    
        # Log all errors
        for error in errors:
            log_data_quality_issue(
                "transformed_data", 
                error["column"], 
                error["message"],
                error.get("count")
            )
            
        return errors


def transform_file(file_path: str, format_name: str = None) -> Dict:
    """Utility function to transform a file
    
    Args:
        file_path: Path to CSV file
        format_name: Optional format name
        
    Returns:
        Transformation results dictionary
    """
    transformer = ReportTransformer()
    df, metadata = transformer.transform(file_path, format_name)
    
    if df.empty:
        return metadata
        
    # Add basic stats
    metadata["row_count"] = len(df)
    metadata["column_count"] = len(df.columns)
    
    return metadata


def main():
    """Command-line interface for report transformation"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Transform CSV reports")
    parser.add_argument("file_path", help="Path to CSV file")
    parser.add_argument("-f", "--format", help="Format name (detected if not provided)")
    parser.add_argument("-o", "--output", help="Output file path")
    
    args = parser.parse_args()
    
    transformer = ReportTransformer()
    df, metadata = transformer.transform(args.file_path, args.format)
    
    if df.empty:
        print(f"Error: {metadata.get('error', 'Unknown error')}")
        return
        
    print(f"Transformation summary:")
    print(f"Format: {metadata['format']}")
    print(f"Rows: {len(df)}")
    print(f"Columns: {len(df.columns)}")
    
    if metadata["validation_errors"]:
        print(f"Validation errors:")
        for error in metadata["validation_errors"]:
            print(f"- {error['message']}")
            
    # Save transformed data if output path provided
    if args.output:
        df.to_csv(args.output, index=False)
        print(f"Transformed data saved to {args.output}")
    else:
        # Print sample rows
        print("\nSample data:")
        print(df.head().to_string())


if __name__ == "__main__":
    main()