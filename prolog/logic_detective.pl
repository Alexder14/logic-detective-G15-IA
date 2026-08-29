% Cargador del motor y fachada de consulta para el backend.
%
%     swipl prolog/logic_detective.pl
%     ?- consulta(caso_demo, responsable(P)).
%     ?- estado_caso(caso1, Estado, Resumen).
%
% Para agregar un caso: su archivo, un ensure_loaded y una linea en
% caso_modulo/1.

:- module(logic_detective,
          [ caso_modulo/1,
            caso_de_ejemplo/1,
            consulta/2,
            estado_caso/3,
            reglas_propias/2,
            minimos_requeridos/5,
            version_motor/1,
            % fachada plana para el backend (una solucion por fila)
            api_caso/10,
            api_caso_de_ejemplo/1,
            api_reglas_propias/2,
            api_sospechoso/4,
            api_indicio/3,
            api_evidencia/7,
            api_evidencia_incrimina/3,
            api_lugar/4,
            api_declaracion/4,
            api_coartada/4,
            api_motivo/3,
            api_relacion/6,
            api_oportunidad/3,
            api_contradiccion/4,
            api_conclusion/3,
            api_veredicto/5,
            api_explicacion/4,
            api_evento/4,
            api_pista/2,
            api_acusacion/4,
            % modulo administrativo: alta/baja de casos y lectura de hechos crudos
            registrar_caso/1,
            olvidar_caso/1,
            vaciar_caso/1,
            api_admin_persona/3,
            api_admin_evidencia/6,
            api_admin_lugar/3,
            api_admin_conexion/3,
            api_admin_coartada/5,
            api_admin_motivo/3,
            api_admin_oportunidad/5,
            api_admin_relacion/4,
            api_admin_declaracion/5,
            api_admin_ficha/3,
            api_admin_hechos/3
          ]).

:- use_module(library(lists)).

% Los casos son modulos con lista de exportacion vacia, asi que cargarlos no
% importa nada a `user` ni choca un nombre con otro. caso1 y caso2 pueden tener
% los mismos sospechosos y lugares sin interferir.
:- ensure_loaded(caso_demo).
:- ensure_loaded(caso1).
:- ensure_loaded(caso2).
:- ensure_loaded(caso3).

%! version_motor(-Version) is det.
version_motor('1.0.0').

%! caso_modulo(?Modulo) is nondet.
%  Casos cargados, en el orden en que se muestran en la interfaz.
%  caso_demo va primero porque es el unico que responde mientras los otros
%  tres esten vacios.
%
%  Dinamico porque el modulo administrativo da de alta y de baja casos con el
%  motor ya corriendo. Las cuatro clausulas de aqui son el catalogo de fabrica.
:- dynamic caso_modulo/1.

caso_modulo(caso_demo).
caso_modulo(caso1).
caso_modulo(caso2).
caso_modulo(caso3).

%! caso_de_ejemplo(?Modulo) is nondet.
%  Casos que existen como referencia y no cuentan entre los tres entregables.
%  No tienen que alcanzar los minimos, asi que estado_caso/3 los reporta
%  incompleto y esta bien: es la unica forma de distinguir "no llega a los
%  minimos" de "no tiene que llegar".
caso_de_ejemplo(caso_demo).

%! minimos_requeridos(-Sospechosos, -Evidencias, -Lugares, -Declaraciones, -Reglas) is det.
%  Minimos por caso segun el enunciado del proyecto.
minimos_requeridos(4, 10, 5, 5, 10).

%! caso_info(?Modulo, -Info) is nondet.
%  Info = caso(Id, Titulo, Descripcion, Dificultad).
%  Si el caso todavia no declara caso/4 devuelve una ficha minima, para que la
%  interfaz pueda listarlo igual.
caso_info(Modulo, Info) :-
    caso_modulo(Modulo),
    (   Modulo:caso(Id, Titulo, Descripcion, Dificultad)
    ->  Info = caso(Id, Titulo, Descripcion, Dificultad)
    ;   Info = caso(Modulo, 'Sin título', 'Caso sin definir.', desconocida)
    ).

%! consulta(+Modulo, +Meta) is nondet.
%  Ejecuta cualquier meta contra el caso indicado. Es la unica puerta que usa
%  el backend, asi que las consultas desde Python se ven todas igual:
%
%      consulta(caso_demo, responsable(P))
%      consulta(caso_demo, nivel_sospecha(Persona, Nivel))
%
%  Falla en vez de lanzar excepcion si el modulo no existe.
consulta(Modulo, Meta) :-
    caso_modulo(Modulo),
    call(Modulo:Meta).

%! reglas_propias(+Modulo, -Cuantas) is det.
%  Cuantas reglas de inferencia declara el caso por su cuenta, sin contar las
%  compartidas de reglas_base.pl. Es el quinto minimo del enunciado, el unico
%  que el modulo administrativo no podia verificar.
%
%  Cada caso incluye reglas_base.pl textualmente (:- include), asi que sus
%  reglas aparecen como definidas en el modulo del caso y no se pueden separar
%  por el modulo. Lo que si las distingue es el archivo de origen de cada
%  clausula, que da clause_property/2.
%
%  Cuenta predicados, no clausulas: un predicado con tres clausulas es una
%  regla con tres casos, no tres reglas. Es el criterio mas conservador de los
%  dos, asi que si este numero alcanza el minimo, alcanza de sobra.
reglas_propias(Modulo, Cuantas) :-
    caso_modulo(Modulo),
    atom_concat(Modulo, '.pl', Archivo),
    findall(Nombre/Aridad,
            (   current_predicate(Modulo:Nombre/Aridad),
                functor(Cabeza, Nombre, Aridad),
                \+ predicate_property(Modulo:Cabeza, imported_from(_)),
                catch(clause(Modulo:Cabeza, Cuerpo, Referencia), _, fail),
                Cuerpo \== true,
                clause_property(Referencia, file(Origen)),
                file_base_name(Origen, Archivo)
            ),
            Predicados),
    sort(Predicados, Unicos),
    length(Unicos, Cuantas).

%! estado_caso(?Modulo, -Estado, -Resumen) is nondet.
%  Estado = pendiente | incompleto | completo
%  Resumen = resumen(Sospechosos, Evidencias, Lugares, Declaraciones, Coartadas)
%
%  - pendiente:  el archivo aun no tiene hechos.
%  - incompleto: tiene hechos pero no alcanza los minimos del enunciado.
%  - completo:   cumple los cinco minimos, incluidas las reglas propias.
%
%  Esto es lo que el modulo administrativo muestra como avance del proyecto.
estado_caso(Modulo, Estado, Resumen) :-
    caso_modulo(Modulo),
    Modulo:resumen_caso(Resumen),
    Resumen = resumen(Sospechosos, Evidencias, Lugares, Declaraciones, _),
    (   Sospechosos =:= 0
    ->  Estado = pendiente
    ;   minimos_requeridos(MinS, MinE, MinL, MinD, MinR),
        Sospechosos >= MinS,
        Evidencias >= MinE,
        Lugares >= MinL,
        Declaraciones >= MinD,
        reglas_propias(Modulo, Reglas),
        Reglas >= MinR
    ->  Estado = completo
    ;   Estado = incompleto
    ).


% =============================================================================
%  FACHADA PLANA PARA EL BACKEND
% =============================================================================
%  Cada api_*/N devuelve una fila por solucion, con argumentos atomicos: nunca
%  listas ni terminos compuestos. Es por PySwip 0.3.x, que no traduce bien los
%  terminos anidados (una lista de atomos dentro de un termino sale como
%  Atom('764549')). Asi cada binding llega a Python como str o int.
%
%  Lo que sea un termino compuesto del dominio (una razon, un motivo, un
%  detalle) se entrega ya convertido a cadena con texto/2.
%
%  La deduccion sigue ocurriendo aqui; Python solo recoge filas.

%! texto(+Termino, -Texto) is det.
texto(Termino, Texto) :-
    term_string(Termino, Texto).

%! api_caso(?Modulo, -Id, -Titulo, -Descripcion, -Dificultad, -Estado,
%!          -NumSospechosos, -NumEvidencias, -NumLugares, -NumDeclaraciones) is nondet.
api_caso(Modulo, Id, Titulo, Descripcion, Dificultad, Estado, NS, NE, NL, ND) :-
    caso_info(Modulo, caso(Id, Titulo, Descripcion, Dificultad)),
    estado_caso(Modulo, Estado, resumen(NS, NE, NL, ND, _)).

%! api_caso_de_ejemplo(?Modulo) is nondet.
%  Fila por caso de referencia, para que la interfaz pueda decir por que no
%  alcanza los minimos.
api_caso_de_ejemplo(Modulo) :-
    caso_de_ejemplo(Modulo).

%! api_reglas_propias(?Modulo, -Cuantas) is nondet.
%  Fila por caso con su cuenta de reglas de inferencia propias.
api_reglas_propias(Modulo, Cuantas) :-
    caso_modulo(Modulo),
    reglas_propias(Modulo, Cuantas).

%! api_sospechoso(+Modulo, -Persona, -Nivel, -Puntaje) is nondet.
%  Ordenados de mayor a menor puntaje por ranking_sospecha/1.
api_sospechoso(Modulo, Persona, Nivel, Puntaje) :-
    consulta(Modulo, ranking_sospecha(Ranking)),
    member(sospecha(Puntaje, Persona, Nivel), Ranking).

%! api_indicio(+Modulo, ?Persona, -Indicio) is nondet.
api_indicio(Modulo, Persona, Indicio) :-
    consulta(Modulo, sospechoso(Persona)),
    consulta(Modulo, indicios(Persona, Indicios)),
    member(Indicio, Indicios).

%! api_evidencia(+Modulo, -Id, -Tipo, -Lugar, -Hora, -Descripcion, -Directa) is nondet.
%  Hora es un entero o el atomo desconocida. Directa = si | no.
api_evidencia(Modulo, Id, Tipo, Lugar, Hora, Descripcion, Directa) :-
    consulta(Modulo, evidencia(Id, Tipo, Lugar, Hora, Descripcion)),
    (   consulta(Modulo, tipo_evidencia_directa(Tipo))
    ->  Directa = si
    ;   Directa = no
    ).

%! api_evidencia_incrimina(+Modulo, ?IdEv, ?Persona) is nondet.
api_evidencia_incrimina(Modulo, IdEv, Persona) :-
    consulta(Modulo, evidencia_incrimina(IdEv, Persona)).

%! api_lugar(+Modulo, -Nombre, -Descripcion, -EsEscena) is nondet.
api_lugar(Modulo, Nombre, Descripcion, EsEscena) :-
    consulta(Modulo, lugar(Nombre, Descripcion)),
    (   consulta(Modulo, escena_del_incidente(Nombre))
    ->  EsEscena = si
    ;   EsEscena = no
    ).

%! api_declaracion(+Modulo, -Id, -Autor, -Contenido) is nondet.
%  Contenido llega como cadena, p.ej. "no_estuvo_en(bruno,laboratorio,14)".
api_declaracion(Modulo, Id, Autor, Contenido) :-
    consulta(Modulo, declaracion(Id, Autor, Termino)),
    texto(Termino, Contenido).

%! api_coartada(+Modulo, -Persona, -Estado, -Detalle) is nondet.
%  Estado = valida | invalida. Detalle es la justificacion o la razon del
%  descarte. Incluye a los sospechosos que no presentaron coartada.
api_coartada(Modulo, Persona, valida, Detalle) :-
    consulta(Modulo, coartada_valida(Persona, Justificacion)),
    texto(Justificacion, Detalle).
api_coartada(Modulo, Persona, invalida, Detalle) :-
    consulta(Modulo, coartada_invalida(Persona, Razon)),
    texto(Razon, Detalle).

%! api_motivo(+Modulo, -Persona, -Motivo) is nondet.
api_motivo(Modulo, Persona, Motivo) :-
    consulta(Modulo, tiene_motivo(Persona, Termino)),
    texto(Termino, Motivo).

%! api_relacion(+Modulo, -Persona, -ConQuien, -Tipo, -Conflictiva, -ConLaVictima) is nondet.
%  Los vinculos entre las personas del caso, tal como estan declarados en
%  relacion/3. Conflictiva = si | no segun relacion_conflictiva/1: es lo que
%  usa tiene_motivo/2 para deducir un motivo cuando no esta declarado, asi que
%  la interfaz puede mostrar por que una relacion pesa. ConLaVictima = si | no
%  ahorra tener que cruzar victima/1 aparte.
api_relacion(Modulo, Persona, ConQuien, Tipo, Conflictiva, ConLaVictima) :-
    consulta(Modulo, relacion(Persona, ConQuien, Tipo)),
    (   consulta(Modulo, relacion_conflictiva(Tipo))
    ->  Conflictiva = si
    ;   Conflictiva = no
    ),
    (   consulta(Modulo, victima(ConQuien))
    ->  ConLaVictima = si
    ;   ConLaVictima = no
    ).

%! api_oportunidad(+Modulo, -Persona, -Lugar) is nondet.
%  Quien pudo cometer el incidente: estuvo o pudo estar en la escena y no tiene
%  una coartada que lo descarte. setof/3 para no repetir una persona cuando las
%  dos clausulas de tuvo_oportunidad/2 se cumplen por caminos distintos.
api_oportunidad(Modulo, Persona, Lugar) :-
    setof(P-L, consulta(Modulo, tuvo_oportunidad(P, L)), Pares),
    member(Persona-Lugar, Pares).

%! api_contradiccion(+Modulo, -Tipo, -A, -B) is nondet.
%  Tipo = entre_declaraciones | declaracion_vs_evidencia.
api_contradiccion(Modulo, Tipo, A, B) :-
    consulta(Modulo, contradicciones(Lista)),
    member(Termino, Lista),
    Termino =.. [Tipo, A, B].

%! api_conclusion(+Modulo, -Clave, -Valor) is nondet.
%  Una fila por elemento de la conclusion:
%      responsable  - persona o 'ninguno'
%      principal    - un sospechoso principal (puede haber empate)
%      complice     - texto "complice de principal"
api_conclusion(Modulo, responsable, Valor) :-
    (   consulta(Modulo, responsable(Persona))
    ->  Valor = Persona
    ;   Valor = ninguno
    ).
api_conclusion(Modulo, principal, Persona) :-
    consulta(Modulo, sospechoso_principal(Persona)).
api_conclusion(Modulo, complice, Texto) :-
    consulta(Modulo, posible_complice(Complice, De)),
    texto(complice(Complice, De), Texto).

%! api_veredicto(+Modulo, ?Persona, -Veredicto, -Nivel, -Puntaje) is nondet.
%  Veredicto = responsable | sospechoso_principal | bajo_investigacion | descartado
api_veredicto(Modulo, Persona, Veredicto, Nivel, Puntaje) :-
    consulta(Modulo, sospechoso(Persona)),
    consulta(Modulo, veredicto(Persona, Veredicto)),
    consulta(Modulo, nivel_sospecha(Persona, Nivel)),
    consulta(Modulo, puntaje_sospecha(Persona, Puntaje)).

%! api_explicacion(+Modulo, ?Persona, -Regla, -Detalle) is nondet.
%  Una fila por regla activada. Es la justificacion de la conclusion.
api_explicacion(Modulo, Persona, Regla, Detalle) :-
    consulta(Modulo, persona(Persona)),
    consulta(Modulo, explicacion(Persona, Traza)),
    member(Elemento, Traza),
    Elemento = regla(Regla, Termino),
    texto(Termino, Detalle).

%! api_evento(+Modulo, -Hora, -Tipo, -Detalle) is nondet.
%  Linea temporal del caso, ordenada por hora.
api_evento(Modulo, Hora, Tipo, Detalle) :-
    consulta(Modulo, linea_temporal(Eventos)),
    member(evento(Hora, Tipo, Termino), Eventos),
    texto(Termino, Detalle).

%! api_pista(+Modulo, -Pista) is nondet.
api_pista(Modulo, Pista) :-
    consulta(Modulo, pista(Termino)),
    texto(Termino, Pista).

%! api_acusacion(+Modulo, +Acusado, -Veredicto, -Responsable) is semidet.
%  Veredicto = correcta | incorrecta | indeterminada | persona_desconocida
%  indeterminada: el motor no reune elementos para senalar a nadie.
api_acusacion(Modulo, Acusado, Veredicto, Responsable) :-
    (   \+ consulta(Modulo, persona(Acusado))
    ->  Veredicto = persona_desconocida, Responsable = ninguno
    ;   consulta(Modulo, responsable(R))
    ->  Responsable = R,
        (   R == Acusado
        ->  Veredicto = correcta
        ;   Veredicto = incorrecta
        )
    ;   Veredicto = indeterminada, Responsable = ninguno
    ).


% =============================================================================
%  FACHADA DEL MODULO ADMINISTRATIVO
% =============================================================================
%  Las api_* de arriba entregan lo que el motor DEDUJO; estas, los hechos tal
%  como estan escritos, porque solo se puede editar lo que alguien declaro: un
%  motivo derivado de una relacion conflictiva no se puede borrar, el motivo/2
%  declarado si.
%
%  El alta y la baja las hace el backend con assertz/retract sobre Modulo:Hecho,
%  que funciona porque reglas_base.pl declara dinamico todo el esquema.

%! hecho_del_esquema(?Nombre/?Aridad) is nondet.
%  El esquema que documenta la cabecera de reglas_base.pl, como datos.
hecho_del_esquema(caso/4).
hecho_del_esquema(sospechoso/1).
hecho_del_esquema(testigo/1).
hecho_del_esquema(victima/1).
hecho_del_esquema(relacion/3).
hecho_del_esquema(lugar/2).
hecho_del_esquema(escena_del_incidente/1).
hecho_del_esquema(hora_del_incidente/1).
hecho_del_esquema(lugar_conectado/2).
hecho_del_esquema(tiene_llave/2).
hecho_del_esquema(autorizado_en/2).
hecho_del_esquema(registro_acceso/3).
hecho_del_esquema(visto_en/3).
hecho_del_esquema(motivo/2).
hecho_del_esquema(medio_requerido/1).
hecho_del_esquema(posee_medio/2).
hecho_del_esquema(evidencia/5).
hecho_del_esquema(evidencia_incrimina/2).
hecho_del_esquema(declaracion/3).
hecho_del_esquema(coartada/4).

%! registrar_caso(+Modulo) is det.
%  Suma un caso al catalogo. Idempotente, a diferencia de un assertz suelto.
registrar_caso(Modulo) :-
    (   caso_modulo(Modulo)
    ->  true
    ;   assertz(caso_modulo(Modulo))
    ).

%! olvidar_caso(+Modulo) is det.
%  Saca el caso del catalogo. El modulo sigue cargado -- SWI no descarga uno
%  incluido -- pero deja de existir para consulta/2 y para el usuario.
olvidar_caso(Modulo) :-
    retractall(caso_modulo(Modulo)).

%! vaciar_caso(+Modulo) is det.
%  Borra los hechos del caso sin tocar sus reglas, para que uno nuevo con el
%  mismo nombre no herede los del anterior.
vaciar_caso(Modulo) :-
    forall(hecho_del_esquema(Nombre/Aridad),
           (   functor(Cabeza, Nombre, Aridad),
               retractall(Modulo:Cabeza)
           )).

%! api_admin_persona(+Modulo, -Persona, -Rol) is nondet.
%  Rol = sospechoso | testigo | victima. Puede aparecer con mas de uno si el
%  caso la declaro asi: el administrador ve los hechos como estan.
api_admin_persona(Modulo, Persona, sospechoso) :-
    consulta(Modulo, sospechoso(Persona)).
api_admin_persona(Modulo, Persona, testigo) :-
    consulta(Modulo, testigo(Persona)).
api_admin_persona(Modulo, Persona, victima) :-
    consulta(Modulo, victima(Persona)).

%! api_admin_evidencia(+Modulo, -Id, -Tipo, -Lugar, -Hora, -Descripcion) is nondet.
api_admin_evidencia(Modulo, Id, Tipo, Lugar, Hora, Descripcion) :-
    consulta(Modulo, evidencia(Id, Tipo, Lugar, Hora, Descripcion)).

%! api_admin_lugar(+Modulo, -Nombre, -Descripcion) is nondet.
api_admin_lugar(Modulo, Nombre, Descripcion) :-
    consulta(Modulo, lugar(Nombre, Descripcion)).

%! api_admin_conexion(+Modulo, -Desde, -Hasta) is nondet.
api_admin_conexion(Modulo, Desde, Hasta) :-
    consulta(Modulo, lugar_conectado(Desde, Hasta)).

%! api_admin_coartada(+Modulo, -Persona, -Lugar, -Hora, -Respaldo) is nondet.
%  La coartada declarada, sin evaluar. Respaldo llega como cadena por ser un
%  termino compuesto: "testigo(bruno_salcedo)".
api_admin_coartada(Modulo, Persona, Lugar, Hora, Respaldo) :-
    consulta(Modulo, coartada(Persona, Lugar, Hora, Termino)),
    texto(Termino, Respaldo).

%! api_admin_motivo(+Modulo, -Persona, -Tipo) is nondet.
api_admin_motivo(Modulo, Persona, Tipo) :-
    consulta(Modulo, motivo(Persona, Tipo)).

%! api_admin_relacion(+Modulo, -Persona, -ConQuien, -Tipo) is nondet.
api_admin_relacion(Modulo, Persona, ConQuien, Tipo) :-
    consulta(Modulo, relacion(Persona, ConQuien, Tipo)).

%! api_admin_declaracion(+Modulo, -Id, -Autor, -Funtor, -Contenido) is nondet.
%  Funtor va aparte del texto completo para que la interfaz elija el formulario
%  sin volver a parsear la cadena.
api_admin_declaracion(Modulo, Id, Autor, Funtor, Contenido) :-
    consulta(Modulo, declaracion(Id, Autor, Termino)),
    functor(Termino, Funtor, _),
    texto(Termino, Contenido).

%! api_admin_oportunidad(+Modulo, -Tipo, -Persona, -Objeto, -Hora) is nondet.
%  Los cinco hechos con los que reglas_base.pl deduce tuvo_oportunidad/2 y
%  capacidad/2. Hora = entero | sin_hora: tres de ellos no llevan hora.
api_admin_oportunidad(Modulo, visto_en, Persona, Lugar, Hora) :-
    consulta(Modulo, visto_en(Persona, Lugar, Hora)).
api_admin_oportunidad(Modulo, registro_acceso, Persona, Lugar, Hora) :-
    consulta(Modulo, registro_acceso(Persona, Lugar, Hora)).
api_admin_oportunidad(Modulo, tiene_llave, Persona, Lugar, sin_hora) :-
    consulta(Modulo, tiene_llave(Persona, Lugar)).
api_admin_oportunidad(Modulo, autorizado_en, Persona, Lugar, sin_hora) :-
    consulta(Modulo, autorizado_en(Persona, Lugar)).
api_admin_oportunidad(Modulo, posee_medio, Persona, Medio, sin_hora) :-
    consulta(Modulo, posee_medio(Persona, Medio)).

%! api_admin_ficha(+Modulo, -Clave, -Valor) is nondet.
%  Los hechos sueltos que configuran el caso: escena, hora y medios exigidos.
api_admin_ficha(Modulo, escena_del_incidente, Lugar) :-
    consulta(Modulo, escena_del_incidente(Lugar)).
api_admin_ficha(Modulo, hora_del_incidente, Hora) :-
    consulta(Modulo, hora_del_incidente(Hora)).
api_admin_ficha(Modulo, medio_requerido, Medio) :-
    consulta(Modulo, medio_requerido(Medio)).

%! api_admin_hechos(+Modulo, +Patron, -Texto) is nondet.
%  Una fila por hecho que unifica con Patron, ya citado y por lo tanto releible.
%  Es lo que permite deshacer una baja: antes de retirar un hecho se guarda su
%  texto, y para restaurarlo se vuelve a afirmar.
api_admin_hechos(Modulo, Patron, Texto) :-
    call(Modulo:Patron),
    texto(Patron, Texto).
