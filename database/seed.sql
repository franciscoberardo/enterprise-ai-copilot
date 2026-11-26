INSERT INTO clientes (nombre, email, pais) VALUES
('Juan Pérez','juan@test.com','Argentina'),
('María Gómez','maria@test.com','Argentina'),
('Pedro López','pedro@test.com','Chile'),
('Ana Martínez','ana@test.com','Uruguay'),
('Carlos Díaz','carlos@test.com','Argentina');

INSERT INTO productos (nombre,categoria,precio,stock) VALUES
('Notebook Lenovo','Computación',1200,18),
('Mouse Logitech','Accesorios',35,120),
('Monitor Samsung 27','Monitores',320,40),
('Teclado Mecánico','Accesorios',90,65),
('Auriculares Sony','Audio',180,30);

INSERT INTO pedidos (cliente_id,fecha,total,estado) VALUES
(1,'2026-07-01',1235,'Entregado'),
(2,'2026-07-03',355,'Pendiente'),
(3,'2026-07-05',410,'Entregado'),
(1,'2026-07-08',180,'Enviado'),
(5,'2026-07-10',1290,'Pendiente');

INSERT INTO detalle_pedidos (pedido_id,producto_id,cantidad,precio) VALUES
(1,1,1,1200),
(1,2,1,35),
(2,3,1,320),
(2,2,1,35),
(3,4,2,180),
(3,2,1,35),
(4,5,1,180),
(5,1,1,1200),
(5,4,1,90);