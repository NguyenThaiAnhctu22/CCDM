# src/helpers/cardinality_helper.py

class CardinalityHelper:
    @staticmethod
    def model_to_combo_string(card_str: str) -> str:
        """Chuyển 'Many-Optional' -> '0,n', 'One-Mandatory' -> '1,1'"""
        is_man = "Mandatory" in card_str
        is_many = "Many" in card_str
        prefix = "1," if is_man else "0,"
        suffix = "n" if is_many else "1"
        return f"{prefix}{suffix}"

    @staticmethod
    def combo_to_model_string(is_mandatory: bool, cb_text: str) -> str:
        """Chuyển (False, '0,n') -> 'Many-Optional'"""
        is_many = "n" in cb_text
        prefix = "Many" if is_many else "One"
        suffix = "Mandatory" if is_mandatory else "Optional"
        return f"{prefix}-{suffix}"

    @staticmethod
    def get_cardinality_description(entity_src: str, entity_tgt: str, combo_text: str) -> str:
        """Sinh ra câu diễn giải ngữ nghĩa cho Dialog"""
        if ",1" in combo_text:
            return f"Each {entity_src} may have at most one {entity_tgt}."
        return f"Each {entity_src} can have many {entity_tgt}."