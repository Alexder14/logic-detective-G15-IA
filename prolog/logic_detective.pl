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
            api_acusacion/4
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
