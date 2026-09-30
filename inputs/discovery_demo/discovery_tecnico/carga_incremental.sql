-- Carga incremental de facturación adquirente
-- Autor: Luis Mora — corte diario 23:00

CREATE TABLE oro.FACTURACION_ADQUIRENTE_DIARIA (
    fecha_proceso DATE,
    comercio_id   VARCHAR(20),
    monto_bruto   DECIMAL(18,2)
);

INSERT INTO oro.FACTURACION_ADQUIRENTE_DIARIA
SELECT  t.fecha, c.comercio_id, SUM(t.monto)
FROM    BACPROD.dbo.TRX_ADQUIRENCIA t
JOIN    BACPROD.dbo.CATALOGO_COMERCIOS c ON t.comercio = c.id
LEFT JOIN BACLIQ.dbo.LIQUIDACIONES l     ON l.trx_id  = t.id
WHERE   t.fecha >= DATEADD(day, -1, GETDATE())
GROUP BY t.fecha, c.comercio_id;
