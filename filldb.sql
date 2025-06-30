-- prerenche o banco de dados inicial
-- use com usuario definido no init

CREATE TABLE computadores(
    porta INTEGER PRIMARY KEY,
    block INTEGER NOT NULL,
    inicio TIMESTAMP,
    fim TIMESTAMP
);

CREATE TABLE mestres(
    porta INTEGER PRIMARY KEY
);

-------- Funções
CREATE OR REPLACE FUNCTION validar_block_mestre()
RETURNS TRIGGER AS $$
BEGIN
    -- Verifica se a porta está na tabela mestres
    IF EXISTS (SELECT 1 FROM mestres WHERE porta = NEW.porta) THEN
        IF NEW.block IS DISTINCT FROM -1 THEN
            RAISE EXCEPTION 'Porta % é mestre e deve ter block = -1', NEW.porta;
        END IF;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger para INSERT
CREATE OR REPLACE TRIGGER trg_validar_block_mestre_insert
BEFORE INSERT ON computadores
FOR EACH ROW
EXECUTE FUNCTION validar_block_mestre();

-- Trigger para UPDATE
CREATE OR REPLACE TRIGGER trg_validar_block_mestre_update
BEFORE UPDATE ON computadores
FOR EACH ROW
EXECUTE FUNCTION validar_block_mestre();

--------- Popular
INSERT INTO mestres (porta) VALUES
(10),
(11);

INSERT INTO computadores (porta, block, inicio, fim) VALUES
(1, 0, NULL, NULL),
(2, 0, NULL, NULL),
(3, 0, NULL, NULL),
(4, 0, NULL, NULL),
(5, 0, NULL, NULL),
(6, 0, NULL, NULL),
-- (7, 0, NULL, NULL), -- quebrada
-- (8, 0, NULL, NULL), -- quebrada
(9, 0, NULL, NULL),
(10, -1, NULL, NULL), -- mestre 1
(11, -1, NULL, NULL), -- mestre 2
(12, 0, NULL, NULL),
(13, 0, NULL, NULL),
(14, 0, NULL, NULL),
(15, 0, NULL, NULL),
(16, 0, NULL, NULL),
(17, 0, NULL, NULL),
(18, 0, NULL, NULL),
(19, 0, NULL, NULL),
(20, 0, NULL, NULL),
(23, 0, NULL, NULL);