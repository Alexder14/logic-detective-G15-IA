% =============================================================================
%  CASO 3 — El servidor saboteado
%  Responsable: Joshua Estuardo Franco Equite
% =============================================================================
%
%  AVANCE — SEMANA 1 (03-07 ago)
%  ---------------------------------------------------------------------------
%  Esta semana toca "modelar sospechosos y hechos del caso" (cronograma,
%  docs/DISTRIBUCION_TRABAJO.md): todo lo de abajo EXCEPTO evidencias,
%  declaraciones y las 10 reglas propias, que quedan para la semana 2 cuando
%  el motor ya pueda llegar a un `responsable/1`.
%
%  Por eso en esta version:
%    - diego_lira acumula acceso + oportunidad + motivo + medios +
%      coartada_invalida (falta solo la evidencia para que responsable/1 lo
%      senale). Probalo con `ranking_sospecha` mas abajo: deberia ir primero.
%    - Los otros tres sospechosos quedan deliberadamente incompletos en al
%      menos una de esas categorias, para que no empaten con diego_lira
%      cuando se agregue la evidencia la semana que viene.
%
%  ARCHIVO PENDIENTE (evidencias, declaraciones, reglas propias). Aquí van
%  SOLO HECHOS y las reglas propias de este caso. Las reglas de inferencia
%  compartidas ya están resueltas en reglas_base.pl y este archivo las hereda
%  con `:- include`. NO copies reglas_base.pl aquí y NO la edites: si
%  necesitas un predicado que no existe, habla con el coordinador.
%
%  ---------------------------------------------------------------------------
%  MÍNIMOS QUE EXIGE EL ENUNCIADO PARA ESTE CASO
%  ---------------------------------------------------------------------------
%
%    [x]  4 sospechosos      -> sospechoso/1
%    [ ] 10 evidencias       -> evidencia/5  (+ evidencia_incrimina/2)      -- semana 2
%    [x]  5 lugares          -> lugar/2
%    [ ]  5 declaraciones    -> declaracion/3                              -- semana 2
%    [ ] 10 reglas de inferencia propias del caso (sección al final)       -- semana 2
%
%  Además, para que el motor pueda concluir algo, este caso NECESITA:
%
%    [x] caso/4                    identidad del caso (ya está abajo)
%    [x] victima/1                 quién sufrió el incidente
%    [x] escena_del_incidente/1    dónde ocurrió
%    [x] hora_del_incidente/1      entero 0..23
%    [x] medio_requerido/1         qué exigió el incidente (al menos uno)
%    [x] coartada/4                una por sospechoso, con o sin respaldo
%    [x] relacion/3                relaciones entre los involucrados
%
%  ---------------------------------------------------------------------------
%  ESQUEMA DE HECHOS
%  ---------------------------------------------------------------------------
%  El contrato completo, con los tipos y valores permitidos de cada argumento,
%  está en el encabezado de `reglas_base.pl`. Respétalo al pie de la letra: las
%  reglas base detectan las contradicciones por unificación sobre esos términos,
%  así que un functor mal escrito hace que el caso simplemente no concluya nada.
%
%  Los términos permitidos dentro de declaracion/3 son:
%      estuvo_en(Persona, Lugar, Hora)      no_estuvo_en(Persona, Lugar, Hora)
%      vio_a(Persona, Lugar, Hora)          conoce_a(P1, P2)
%      no_conoce_a(P1, P2)                  posee(Persona, Medio)
%
%  ---------------------------------------------------------------------------
%  DISEÑA EL CASO ANTES DE ESCRIBIRLO
%  ---------------------------------------------------------------------------
%  Un caso está bien construido si el motor llega a UN solo responsable y ese
%  responsable es el que tú querías. Para eso el culpable debe acumular
%  oportunidad + motivo + medios + coartada inválida + al menos 2 evidencias, y
%  los otros tres sospechosos deben quedar por debajo. Los distractores se
%  construyen dándoles una o dos de esas cosas, nunca todas.
%
%  Ver `caso_demo.pl` como ejemplo mínimo de formato (NO como ejemplo de
%  tamaño: ese caso no cumple los mínimos).
%
%  ---------------------------------------------------------------------------
%  CÓMO PROBAR TU CASO
%  ---------------------------------------------------------------------------
%      swipl prolog/caso3.pl
%      ?- caso3:resumen_caso(R).                  % verifica los conteos mínimos
%      ?- caso3:ranking_sospecha(R).              % revisa que el orden sea el que buscas
%      ?- caso3:responsable(P).                   % debe dar UNA sola respuesta
%      ?- caso3:contradicciones(C).
%      ?- caso3:explicacion(P, E), forall(member(R,E), (print(R), nl)).
%
%  Y desde el navegador, con el sistema levantado:
%      http://localhost:8080/investigacion/caso3
%
% =============================================================================

:- module(caso3, []).

:- include('reglas_base.pl').


% --- Identidad --------------------------------------------------------------
caso(caso3,
     'El servidor saboteado',
     'A las 2:00 a.m., durante una ventana de mantenimiento, alguien corrompió deliberadamente los archivos de configuración del servidor principal de NexaCorp, tirando el sistema y arruinando la migración que lideraba la ingeniera Paola Ríos. ¿Quién tuvo acceso a la sala de servidores esa noche, y por qué?',
     media).


% --- Personas ---------------------------------------------------------------
%  sospechoso/1, testigo/1, victima/1, relacion/3
%
%  4 sospechosos, todos con llegada plausible a la sala de servidores:
%    diego_lira     contratista de TI, le avisaron que no le renuevan
%    renata_soto    sysadmin, le debe dinero a la victima (deudor: relacion
%                   conflictiva -> tiene_motivo se deriva sola, no hace falta
%                   un motivo/2 aparte para ella)
%    bruno_paredes  guardia de seguridad, acceso a todo el edificio
%    ana_lucero     sysadmin junior, amiga de la victima, se fue temprano

sospechoso(diego_lira).
sospechoso(renata_soto).
sospechoso(bruno_paredes).
sospechoso(ana_lucero).

testigo(carlos_vega).            % guardia del turno nocturno, no es sospechoso

victima(paola_rios).             % jefa de sistemas, responsable del proyecto perdido

relacion(diego_lira,    paola_rios, empleado).   % contratista bajo su supervision
relacion(renata_soto,   paola_rios, deudor).     % conflictiva -> motivo derivado
relacion(bruno_paredes, paola_rios, empleado).
relacion(ana_lucero,    paola_rios, amigo).


% --- Lugares y tiempo -------------------------------------------------------
%  lugar/2, escena_del_incidente/1, hora_del_incidente/1, lugar_conectado/2
%
%  Cadena sala_servidores - pasillo - {oficina_ti, recepcion} - estacionamiento.
%  Nadie necesita la adyacencia para llegar a la escena (todos los que tienen
%  acceso lo tienen directo), pero queda para que `alcanzable/2` tenga algo
%  que recorrer si alguien prueba consultas de ruta.

lugar(sala_servidores,    'Sala de servidores principal de NexaCorp').
lugar(oficina_ti,         'Oficina del equipo de TI, contigua a la sala de servidores').
lugar(pasillo_datacenter, 'Pasillo de acceso restringido del datacenter').
lugar(recepcion,          'Recepción y caseta de vigilancia del edificio').
lugar(estacionamiento,    'Estacionamiento de empleados').

escena_del_incidente(sala_servidores).
hora_del_incidente(2).

lugar_conectado(sala_servidores, pasillo_datacenter).
lugar_conectado(pasillo_datacenter, oficina_ti).
lugar_conectado(pasillo_datacenter, recepcion).
lugar_conectado(recepcion, estacionamiento).


% --- Acceso -----------------------------------------------------------------
%  tiene_llave/2, autorizado_en/2, registro_acceso/3
%
%  diego_lira es el UNICO con tiene_llave directo a la escena: eso le da
%  acceso_al_lugar/2 por la primera clausula de reglas_base, sin necesitar la
%  ruta recursiva. bruno tiene autorizado_en (acceso, pero a todo el
%  edificio, no prueba nada por si solo). renata y ana solo tienen
%  registro_acceso a oficina_ti, un lugar distinto de la escena: acceso_al_lugar
%  exige que el lugar del registro sea la escena, asi que a ellas NO les
%  cuenta como acceso a sala_servidores.

tiene_llave(diego_lira, sala_servidores).
autorizado_en(bruno_paredes, sala_servidores).
registro_acceso(renata_soto, oficina_ti, 1).
registro_acceso(ana_lucero, oficina_ti, 23).


% --- Presencia --------------------------------------------------------------
%  visto_en/3
%
%  A bruno lo capta la camara de recepcion A LA MISMA HORA del incidente, en
%  otro lugar: eso activa ubicado_fuera_de_la_escena/1 y le bloquea la
%  oportunidad aunque tenga acceso. A diego, en cambio, nadie lo ve en ningun
%  lado esa noche -- ni en la escena ni fuera de ella -- que es justo el hueco
%  que la clausula (b) de tuvo_oportunidad/2 esta pensada para cubrir.

visto_en(bruno_paredes, recepcion, 2).


% --- Motivo -----------------------------------------------------------------
%  motivo/2
%
%  El de renata_soto no hace falta declararlo aqui: sale solo de la relacion
%  deudor con la victima (ver mas arriba, y tiene_motivo/2 en reglas_base).

motivo(diego_lira, despido).


% --- Medios -----------------------------------------------------------------
%  medio_requerido/1, posee_medio/2
%
%  El sabotaje pudo hacerse con acceso fisico a la consola (llave) o de forma
%  remota si sabias lo que estabas tocando (conocimiento_tecnico). diego_lira
%  cumple las dos: la de llave se la da gratis reglas_base (tiene_llave en la
%  escena + medio_requerido(llave)); la de conocimiento_tecnico se declara
%  aqui porque el motor no la puede derivar de otro hecho.

medio_requerido(llave).
medio_requerido(conocimiento_tecnico).

posee_medio(diego_lira, conocimiento_tecnico).


% --- Evidencias -------------------------------------------------------------
%  evidencia/5, evidencia_incrimina/2                                  -- semana 2
%  Pendiente: minimo 10, con al menos 2 senalando a diego_lira para que
%  responsable/1 tenga con que concluir (exige N >= 2).


% --- Declaraciones ----------------------------------------------------------
%  declaracion/3                                                       -- semana 2
%  Pendiente: minimo 5, usando los terminos permitidos del encabezado de
%  reglas_base.pl (estuvo_en, no_estuvo_en, vio_a, conoce_a, no_conoce_a, posee).


% --- Coartadas --------------------------------------------------------------
%  coartada/4
%
%  Una fila por sospechoso, como exige el enunciado. La de diego_lira es la
%  unica sin respaldo real: dice haber estado en el estacionamiento pero no
%  tiene con que probarlo, asi que coartada_invalida/2 la marca `sin_respaldo`
%  y -- justo porque el respaldo no cuenta -- coartada_valida/2 nunca se activa
%  para el, dejando abierta la clausula (b) de tuvo_oportunidad/2.

coartada(diego_lira,    estacionamiento,    2, ninguno).
coartada(renata_soto,   oficina_ti,         1, testigo(carlos_vega)).
coartada(bruno_paredes, recepcion,          2, camara(recepcion)).
coartada(ana_lucero,    oficina_ti,        23, testigo(carlos_vega)).


% =============================================================================
%  REGLAS DE INFERENCIA PROPIAS DEL CASO 3  (mínimo 10)
% =============================================================================
%  Aquí van las reglas que solo tienen sentido en este caso y que no cabían en
%  reglas_base.pl. Constrúyelas SOBRE los predicados base, no en paralelo a
%  ellos. Ideas de reglas que suman a la rúbrica (usa listas, recursividad,
%  negación y algún corte):
%
%    - un rol específico del caso (turno_nocturno/1, tiene_acceso_al_sistema/1)
%    - una regla que combine dos evidencias del caso para una conclusión nueva
%    - una regla recursiva sobre relacion/3 (quién encubre a quién, en cadena)
%    - una regla con \+ que descarte a un sospechoso por una razón del caso
%    - una regla con findall/length que exija un mínimo de evidencias
%
%  Documenta cada regla con un comentario de una línea: la rúbrica califica que
%  el uso de listas, recursividad, unificación, negación y cortes sea
%  comprobable.
