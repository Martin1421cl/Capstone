from ksecure.validators.rut import RutValidator, calcular_dv


class TestCalcularDV:
    def test_dv_numerico(self):
        assert calcular_dv(12345678) == "5"

    def test_dv_k(self):
        assert calcular_dv(1000005) == "K"

    def test_dv_cero(self):
        # Caso donde el resto de Módulo 11 es 0 -> DV "0"
        assert calcular_dv(1000013) == "0"


class TestRutValidatorFormato:
    def setup_method(self):
        self.validator = RutValidator()

    def test_detecta_formato_con_puntos_y_guion(self):
        findings = self.validator.find("RUT del cliente: 12.345.678-5", "test")
        assert len(findings) == 1
        assert findings[0].normalized_value == "12345678-5"

    def test_detecta_formato_sin_puntos(self):
        findings = self.validator.find("Identificación: 12345678-5", "test")
        assert len(findings) == 1

    def test_no_detecta_numero_sin_guion(self):
        # Sin guion no hay forma confiable de separar cuerpo y DV.
        findings = self.validator.find("Código de producto: 123456789", "test")
        assert findings == []


class TestRutValidatorModulo11:
    def setup_method(self):
        self.validator = RutValidator()

    def test_dv_valido_marca_is_valid_true(self):
        findings = self.validator.find("RUT 12.345.678-5", "test")
        assert findings[0].is_valid is True

    def test_dv_invalido_marca_is_valid_false(self):
        # 11.111.111 tiene DV real "1", probamos con un DV incorrecto (2)
        findings = self.validator.find("RUT 11.111.111-2", "test")
        assert findings[0].is_valid is False
        assert findings[0].risk_level.value == "Interno"

    def test_dv_valido_se_clasifica_restringido(self):
        findings = self.validator.find("RUT del paciente: 12.345.678-5", "test")
        assert findings[0].risk_level.value == "Restringido"


class TestRutValidatorContexto:
    def setup_method(self):
        self.validator = RutValidator()

    def test_palabra_clave_positiva_sube_confianza(self):
        sin_contexto = self.validator.find("12.345.678-5", "test")[0]
        con_contexto = self.validator.find(
            "El RUT del cliente es 12.345.678-5", "test"
        )[0]
        assert con_contexto.confidence_score > sin_contexto.confidence_score

    def test_palabra_clave_negativa_baja_confianza(self):
        sin_contexto = self.validator.find("12.345.678-5", "test")[0]
        con_negativo = self.validator.find(
            "Folio de la boleta 12.345.678-5", "test"
        )[0]
        assert con_negativo.confidence_score < sin_contexto.confidence_score

    def test_cuerpo_fuera_de_rango_se_descarta(self):
        # Cuerpo de 1 dígito con guion no es un RUT plausible.
        findings = self.validator.find("2-5", "test")
        assert findings == []
