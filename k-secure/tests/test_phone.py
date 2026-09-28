from ksecure.validators.phone import PhoneValidator


class TestPhoneValidator:
    def setup_method(self):
        self.validator = PhoneValidator()

    def test_detecta_con_prefijo_internacional(self):
        findings = self.validator.find("Contacto: +56 9 8765 4321", "test")
        assert len(findings) == 1
        assert findings[0].normalized_value == "+56 9 8765 4321"

    def test_detecta_sin_prefijo(self):
        findings = self.validator.find("Celular 987654321", "test")
        assert len(findings) == 1

    def test_prefijo_internacional_sube_confianza(self):
        con_prefijo = self.validator.find("+56987654321", "test")[0]
        sin_prefijo = self.validator.find("987654321 dato suelto", "test")[0]
        assert con_prefijo.confidence_score >= sin_prefijo.confidence_score

    def test_no_detecta_numero_que_no_empieza_en_9(self):
        findings = self.validator.find("Código de área 812345678", "test")
        assert findings == []
