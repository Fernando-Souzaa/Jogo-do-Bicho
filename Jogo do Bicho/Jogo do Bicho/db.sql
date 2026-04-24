CREATE DATABASE IF NOT EXISTS banco_dados;
USE banco_dados;

CREATE TABLE IF NOT EXISTS usuarios (
    id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(100) NOT NULL UNIQUE,
    email VARCHAR(150) UNIQUE,
    senha VARCHAR(255) NOT NULL,
    saldo DECIMAL(10,2) NOT NULL DEFAULT 0,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS eventos (
    id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    data_evento DATETIME,
    grupo_resultado INT,
    dezena_resultado VARCHAR(2),
    status ENUM('ABERTO', 'ENCERRADO') DEFAULT 'ABERTO'
);

CREATE TABLE IF NOT EXISTS apostas (
    id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    usuario_id INT NOT NULL,
    evento_id INT NOT NULL,
    grupo INT,
    dezena VARCHAR(2),
    tipo ENUM('GRUPO', 'DEZENA') NOT NULL,
    valor DECIMAL(10,2) NOT NULL,
    status ENUM('PENDENTE', 'GANHA', 'PERDIDA') DEFAULT 'PENDENTE',
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (evento_id) REFERENCES eventos(id),
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE
);

-- eventos iniciais
INSERT INTO eventos (nome, data_evento, status)
VALUES 
("Jogo do Bicho - 11h", NOW(), "ABERTO"),
("Jogo do Bicho - 14h", NOW(), "ABERTO"),
("Jogo do Bicho - 16h", NOW(), "ABERTO"),
("Jogo do Bicho - 18h", NOW(), "ABERTO");

UPDATE apostas a
JOIN eventos e ON a.evento_id = e.id
SET a.status =
    CASE
        WHEN a.tipo = 'GRUPO' AND a.grupo = e.grupo_resultado THEN 'GANHA'
        WHEN a.tipo = 'DEZENA' AND a.dezena = e.dezena_resultado THEN 'GANHA'
        ELSE 'PERDIDA'
    END
WHERE e.id = 1;

SELECT 
    a.id AS aposta_id,
    a.evento_id,
    e.nome AS evento,
    a.grupo,
    a.dezena,
    a.valor,
    a.status,
    a.criado_em
FROM apostas a
JOIN eventos e ON e.id = a.evento_id
ORDER BY a.criado_em DESC;
