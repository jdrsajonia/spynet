Pon aquí tus imágenes (esta carpeta `public/` la sirve Vite en la raíz "/"):

  logo.png      -> reemplaza el ícono junto a "SPYNET" en la barra lateral.
  scanning.png  -> imagen central que se muestra mientras corre el análisis.

En el código se referencian como  /logo.png  y  /scanning.png.

Puedes usar .png / .jpg / .svg / .webp. Si usas otra extensión, cambia el
`src` en el código:
  - logo:     frontend/src/components/Sidebar.jsx   (src="/logo.png")
  - scanning: frontend/src/components/Scanning.jsx  (src="/scanning.png")

Mientras no exista la imagen, simplemente no se muestra (no sale ícono roto).
