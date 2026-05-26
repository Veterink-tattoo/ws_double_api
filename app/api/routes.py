from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta, timezone
from typing import Optional, Union, List, Dict
from pydantic import BaseModel, Field


from app.db.session import get_db
from app.db.models import DoubleSpin
from app.api.dependencies import verify_api_key
from app.core.websocket_manager import manager

router = APIRouter(dependencies=[Depends(verify_api_key)])

# Offset fixo para Brasília (UTC-3)
BRT_OFFSET = timedelta(hours=3)

def _utc_now() -> datetime:
    """Retorna o horário UTC atual (naive)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)

def _day_start_utc(date_str: Optional[str] = None) -> datetime:
    """Retorna o início de um dia em Brasília, convertido para UTC."""
    if date_str:
        try:
            target_date = datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(
                status_code=400, 
                detail="Formato de data inválido. Use YYYY-MM-DD."
            )
    else:
        target_date = _utc_now() - BRT_OFFSET
    start_brt = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
    return start_brt + BRT_OFFSET  # Transforma em UTC

@router.get("/results")
async def get_results(
    limit: int = Query(100, le=1000, description="Quantidade de giros retornados"), 
    db: AsyncSession = Depends(get_db)
):
    """Retorna os giros mais recentes gravados no banco de dados."""
    stmt = select(DoubleSpin).order_by(DoubleSpin.id.desc()).limit(limit)
    result = await db.execute(stmt)
    spins = result.scalars().all()
    
    data = []
    for s in spins:
        data.append({
            "id": s.id,
            "roll": s.roll,
            "color": s.color,
            "color_name": "Branco" if s.color == 0 else "Vermelho" if s.color == 1 else "Preto",
            "created_at": s.created_at.isoformat() + "Z"
        })
        
    return {
        "success": True,
        "count": len(data),
        "data": data
    }

@router.get("/stats")
async def get_stats(
    date: Optional[str] = Query(None, description="Data no formato YYYY-MM-DD. Se omitido, usa hoje."),
    db: AsyncSession = Depends(get_db)
):
    """Retorna a estatística percentual de cores agrupadas hora a hora em Brasília (BRT)."""
    day_start_utc = _day_start_utc(date)
    day_end_utc = day_start_utc + timedelta(days=1)
    
    # Filtra spins do dia especificado
    stmt = (
        select(DoubleSpin)
        .where(DoubleSpin.created_at >= day_start_utc)
        .where(DoubleSpin.created_at < day_end_utc)
        .order_by(DoubleSpin.id.desc())
    )
    result = await db.execute(stmt)
    spins = result.scalars().all()
    
    # Agrupador hora a hora
    hourly_stats = {i: {"white": 0, "red": 0, "black": 0, "total": 0} for i in range(24)}
    
    for s in spins:
        local_time = s.created_at - BRT_OFFSET
        hour = local_time.hour
        hourly_stats[hour]["total"] += 1
        if s.color == 0: 
            hourly_stats[hour]["white"] += 1
        elif s.color == 1: 
            hourly_stats[hour]["red"] += 1
        elif s.color == 2: 
            hourly_stats[hour]["black"] += 1
        
    final_data = []
    for hour in range(24):
        stats = hourly_stats[hour]
        total = stats["total"]
        
        if total == 0:
            final_data.append({"hour": hour, "white": "-", "red": "-", "black": "-"})
        else:
            final_data.append({
                "hour": hour,
                "white": f"{round((stats['white'] / total) * 100)}%",
                "red": f"{round((stats['red'] / total) * 100)}%",
                "black": f"{round((stats['black'] / total) * 100)}%"
            })
            
    return {"success": True, "data": final_data}

@router.get("/history/{hour}")
async def get_history_by_hour(
    hour: int,
    date: Optional[str] = Query(None, description="Data no formato YYYY-MM-DD. Se omitido, usa hoje."),
    db: AsyncSession = Depends(get_db)
):
    """Retorna o histórico detalhado de giros de uma determinada hora específica de Brasília (BRT)."""
    if not (0 <= hour <= 23):
        raise HTTPException(status_code=400, detail="A hora fornecida deve estar entre 0 e 23.")

    day_start_utc = _day_start_utc(date)
    hour_start_utc = day_start_utc + timedelta(hours=hour)
    hour_end_utc = hour_start_utc + timedelta(hours=1)
    
    stmt = (
        select(DoubleSpin)
        .where(DoubleSpin.created_at >= hour_start_utc)
        .where(DoubleSpin.created_at < hour_end_utc)
        .order_by(DoubleSpin.id.desc())
    )
    result = await db.execute(stmt)
    spins = result.scalars().all()
    
    data = []
    for s in spins:
        data.append({
            "id": s.id,
            "roll": s.roll,
            "color": s.color,
            "color_name": "Branco" if s.color == 0 else "Vermelho" if s.color == 1 else "Preto",
            "created_at": s.created_at.isoformat() + "Z"
        })
            
    return {
        "success": True,
        "count": len(data),
        "data": data
    }

@router.get("/fullday")
async def get_fullday(
    date: Optional[str] = Query(None, description="Data no formato YYYY-MM-DD. Se omitido, usa hoje."),
    db: AsyncSession = Depends(get_db)
):
    """Retorna os resultados completos de um dia inteiro agrupados por hora e minuto de Brasília (BRT)."""
    day_start_utc = _day_start_utc(date)
    day_end_utc = day_start_utc + timedelta(days=1)

    stmt = (
        select(DoubleSpin)
        .where(DoubleSpin.created_at >= day_start_utc)
        .where(DoubleSpin.created_at < day_end_utc)
        .order_by(DoubleSpin.id.desc())
    )
    result = await db.execute(stmt)
    spins = result.scalars().all()

    data = []
    for s in spins:
        local_time = s.created_at - BRT_OFFSET
        data.append({
            "id": s.id,
            "roll": s.roll,
            "color": s.color,
            "hour": local_time.hour,
            "minute": local_time.minute,
            "created_at": s.created_at.isoformat() + "Z"
        })
    return {"success": True, "count": len(data), "data": data}


# --- SCHEMAS E ENDPOINTS PARA MONITORAMENTO E ESTRATÉGIAS ---

class BacktestRequest(BaseModel):
    trigger_type: str = Field(..., description="Tipo de gatilho, e.g. 'number_draw' ou 'color_sequence'")
    trigger_value: Union[int, List[int]] = Field(..., description="Valor do gatilho (número sorteado ou sequência de cores)")
    entry_color: int = Field(..., description="Cor de entrada, 0=Branco, 1=Vermelho, 2=Preto")
    max_gales: int = Field(2, ge=0, le=2, description="Quantidade máxima de Martingales permitidos")
    period_days: int = Field(10, ge=1, le=10, description="Dias de histórico para backtest (1 a 10)")
    strategy_type: Optional[str] = Field(None, description="minuto ou contagem. Se omitido, inferido de trigger_value")

@router.get("/patterns")
async def get_patterns(
    db: AsyncSession = Depends(get_db)
):
    """
    Retorna estatísticas de atrasos ativos (delays) de cores 
    e a sequência (streak) de repetição atual de giros recentes.
    """
    # Busca os 500 giros mais recentes
    stmt = select(DoubleSpin).order_by(DoubleSpin.id.desc()).limit(500)
    result = await db.execute(stmt)
    spins = result.scalars().all()
    
    delays = {"white": 500, "red": 500, "black": 500}
    found = {"white": False, "red": False, "black": False}
    
    # 0=Branco, 1=Vermelho, 2=Preto
    color_map = {0: "white", 1: "red", 2: "black"}
    
    for idx, s in enumerate(spins):
        c_name = color_map.get(s.color)
        if c_name and not found[c_name]:
            delays[c_name] = idx
            found[c_name] = True
        if all(found.values()):
            break
            
    # Streak atual (giros consecutivos da mesma cor a partir do mais recente)
    current_streak = {"color": "white", "length": 0}
    if spins:
        first_color = spins[0].color
        first_color_name = color_map.get(first_color, "white")
        streak_len = 0
        for s in spins:
            if s.color == first_color:
                streak_len += 1
            else:
                break
        current_streak = {"color": first_color_name, "length": streak_len}
        
    return {
        "success": True,
        "delays": delays,
        "current_streak": current_streak
    }

@router.post("/backtest")
async def run_backtest(
    payload: BacktestRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Simula estratégias no histórico do banco de dados (até 10 dias)
    e retorna a assertividade direta e com Martingales.
    """
    days = payload.period_days
    if not (1 <= days <= 10):
        raise HTTPException(status_code=400, detail="Período de amostra deve ser entre 1 e 10 dias.")
        
    day_start_utc = _utc_now() - timedelta(days=days)
    
    # Busca histórico ordenado cronologicamente (antigo para novo)
    stmt = (
        select(DoubleSpin)
        .where(DoubleSpin.created_at >= day_start_utc)
        .order_by(DoubleSpin.id.asc())
    )
    result = await db.execute(stmt)
    spins = result.scalars().all()
    
    if not spins:
        return {
            "success": True,
            "metrics": {
                "total_signals": 0,
                "win_rate_direct": 0.0,
                "win_rate_gale1": 0.0,
                "win_rate_gale2": 0.0,
                "total_greens": 0,
                "total_reds": 0,
                "max_consecutive_greens": 0,
                "max_consecutive_reds": 0
            }
        }
        
    # Resolve strategy_type
    strat_type = payload.strategy_type
    if not strat_type:
        if isinstance(payload.trigger_value, int) and payload.trigger_value == 6:
            strat_type = "contagem"
        else:
            strat_type = "minuto"
            
    total_signals = 0
    total_greens = 0
    total_reds = 0
    total_direct_wins = 0
    total_gale1_wins = 0
    total_gale2_wins = 0
    
    consecutive_greens = 0
    max_consecutive_greens = 0
    consecutive_reds = 0
    max_consecutive_reds = 0
    
    n_spins = len(spins)
    color_map = {0: "white", 1: "red", 2: "black"}
    
    i = 0
    while i < n_spins:
        triggered = False
        if payload.trigger_type == "number_draw":
            if isinstance(payload.trigger_value, int):
                triggered = (spins[i].roll == payload.trigger_value)
            elif isinstance(payload.trigger_value, list):
                triggered = (spins[i].roll in payload.trigger_value)
        elif payload.trigger_type == "color_sequence":
            if isinstance(payload.trigger_value, list):
                seq_len = len(payload.trigger_value)
                if i >= seq_len - 1:
                    match = True
                    for offset in range(seq_len):
                        if spins[i - (seq_len - 1 - offset)].color != payload.trigger_value[offset]:
                            match = False
                            break
                    triggered = match
                    
        if not triggered:
            i += 1
            continue
            
        win = False
        win_level = -1
        skipped = False
        entry_idx = -1
        
        if strat_type == "minuto":
            trigger_local = spins[i].created_at - BRT_OFFSET
            target_local_start = trigger_local.replace(second=0, microsecond=0) + timedelta(minutes=4)
            target_local_end = target_local_start + timedelta(seconds=59, microseconds=999999)
            
            # Procura o primeiro spin que cai no minuto alvo
            for j in range(i + 1, n_spins):
                local_j = spins[j].created_at - BRT_OFFSET
                if target_local_start <= local_j <= target_local_end:
                    entry_idx = j
                    break
                elif local_j > target_local_end:
                    break
                    
            if entry_idx == -1:
                skipped = True
            else:
                if spins[entry_idx].color == payload.entry_color:
                    win = True
                    win_level = 0
                elif payload.max_gales >= 1 and entry_idx + 1 < n_spins:
                    if spins[entry_idx + 1].color == payload.entry_color:
                        win = True
                        win_level = 1
                    elif payload.max_gales >= 2 and entry_idx + 2 < n_spins:
                        if spins[entry_idx + 2].color == payload.entry_color:
                            win = True
                            win_level = 2
                        else:
                            win = False
                    else:
                        if payload.max_gales >= 2 and entry_idx + 2 >= n_spins:
                            skipped = True
                        else:
                            win = False
                else:
                    if payload.max_gales >= 1 and entry_idx + 1 >= n_spins:
                        skipped = True
                    else:
                        win = False
                        
            if skipped:
                i += 1
                continue
                
        elif strat_type == "contagem":
            entry_idx = i + 5
            if entry_idx >= n_spins:
                i += 1
                continue
                
            if spins[entry_idx].color == payload.entry_color:
                win = True
                win_level = 0
            elif payload.max_gales >= 1 and entry_idx + 1 < n_spins:
                if spins[entry_idx + 1].color == payload.entry_color:
                    win = True
                    win_level = 1
                elif payload.max_gales >= 2 and entry_idx + 2 < n_spins:
                    if spins[entry_idx + 2].color == payload.entry_color:
                        win = True
                        win_level = 2
                    else:
                        win = False
                else:
                    if payload.max_gales >= 2 and entry_idx + 2 >= n_spins:
                        skipped = True
                    else:
                        win = False
            else:
                if payload.max_gales >= 1 and entry_idx + 1 >= n_spins:
                    skipped = True
                else:
                    win = False
                    
            if skipped:
                i += 1
                continue
                
        total_signals += 1
        if win:
            total_greens += 1
            if win_level == 0:
                total_direct_wins += 1
            elif win_level == 1:
                total_gale1_wins += 1
            elif win_level == 2:
                total_gale2_wins += 1
                
            consecutive_greens += 1
            max_consecutive_greens = max(max_consecutive_greens, consecutive_greens)
            consecutive_reds = 0
        else:
            total_reds += 1
            consecutive_reds += 1
            max_consecutive_reds = max(max_consecutive_reds, consecutive_reds)
            consecutive_greens = 0
            
        # Avança o cursor até após o último spin avaliado
        last_evaluated_idx = entry_idx
        if win_level == 1:
            last_evaluated_idx = entry_idx + 1
        elif win_level == 2 or (not win and payload.max_gales == 2):
            last_evaluated_idx = entry_idx + 2
        elif not win and payload.max_gales == 1:
            last_evaluated_idx = entry_idx + 1
            
        i = max(i + 1, last_evaluated_idx + 1)
        
    win_rate_direct = round((total_direct_wins / total_signals) * 100, 1) if total_signals > 0 else 0.0
    win_rate_gale1 = round(((total_direct_wins + total_gale1_wins) / total_signals) * 100, 1) if total_signals > 0 else 0.0
    win_rate_gale2 = round(((total_direct_wins + total_gale1_wins + total_gale2_wins) / total_signals) * 100, 1) if total_signals > 0 else 0.0
    
    return {
        "success": True,
        "metrics": {
            "total_signals": total_signals,
            "win_rate_direct": win_rate_direct,
            "win_rate_gale1": win_rate_gale1,
            "win_rate_gale2": win_rate_gale2,
            "total_greens": total_greens,
            "total_reds": total_reds,
            "max_consecutive_greens": max_consecutive_greens,
            "max_consecutive_reds": max_consecutive_reds
        }
    }


class StrategyStatsRequest(BaseModel):
    strategy: str  # "rider_onix" ou "scarlet_onix"
    entry_color: int  # 0=Branco, 1=Vermelho, 2=Preto
    max_gales: int  # 0 a 3
    date: Optional[str] = None  # YYYY-MM-DD
    hour: Optional[int] = None  # 0 a 23


class HourlyMetric(BaseModel):
    win_rate: float
    total_signals: int


class StrategyStatsResponse(BaseModel):
    success: bool
    win_rate: float
    total_signals: int
    sg: int
    g1: int
    g2: int
    g3: int
    loss: int
    hourly: Dict[int, HourlyMetric]


@router.post("/strategy-stats", response_model=StrategyStatsResponse)
async def run_strategy_stats(payload: StrategyStatsRequest, db: AsyncSession = Depends(get_db)):
    # 1. Determinar datas de início e fim no fuso de Brasília (BRT)
    if payload.date:
        try:
            base_date = datetime.strptime(payload.date, "%Y-%m-%d")
        except ValueError:
            base_date = _utc_now() - BRT_OFFSET
    else:
        base_date = _utc_now() - BRT_OFFSET
        
    start_brt = base_date.replace(hour=0, minute=0, second=0, microsecond=0)
    end_brt = base_date.replace(hour=23, minute=59, second=59, microsecond=999999)
        
    # Converter para UTC
    start_utc = start_brt + BRT_OFFSET
    end_utc = end_brt + BRT_OFFSET
    
    # 2. Buscar giros com tolerância de +15 minutos para avaliar Gales de borda
    stmt = (
        select(DoubleSpin)
        .where(DoubleSpin.created_at >= start_utc)
        .where(DoubleSpin.created_at <= end_utc + timedelta(minutes=15))
        .order_by(DoubleSpin.id.asc())
    )
    result = await db.execute(stmt)
    spins = result.scalars().all()
    
    # Inicializar contadores por hora (0 a 23)
    hourly_data = {
        h: {"sg": 0, "g1": 0, "g2": 0, "g3": 0, "loss": 0, "total": 0}
        for h in range(24)
    }
    
    num_spins = len(spins)
    last_signal_time = None
    
    for i in range(num_spins):
        s = spins[i]
        
        # O gatilho precisa estar estritamente dentro da janela do dia selecionado
        if not (start_utc <= s.created_at <= end_utc):
            continue
            
        triggered = False
        if payload.strategy == "rider_onix":
            if s.roll == 4:
                triggered = True
        elif payload.strategy == "scarlet_onix":
            if s.roll == 6:
                triggered = True
                
        if not triggered:
            continue
            
        # Evitar re-sinalizar no mesmo minuto/momento se já houve sinal recente
        if last_signal_time and (s.created_at - last_signal_time) < timedelta(minutes=2):
            continue
            
        # Determinar índice de entrada
        entry_idx = -1
        if payload.strategy == "rider_onix":
            local_time = s.created_at - BRT_OFFSET
            target_min = (local_time.minute + 4) % 60
            target_hr = (local_time.hour + (1 if local_time.minute + 4 >= 60 else 0)) % 24
            
            for k in range(i + 1, num_spins):
                s_future = spins[k]
                s_future_local = s_future.created_at - BRT_OFFSET
                if s_future_local.minute == target_min and s_future_local.hour == target_hr:
                    entry_idx = k
                    break
        elif payload.strategy == "scarlet_onix":
            # 6ª casa a partir do próprio 6 (ou seja, i + 5)
            if i + 5 < num_spins:
                entry_idx = i + 5
                
        if entry_idx == -1 or entry_idx >= num_spins:
            continue
            
        # Registrar sinal
        last_signal_time = s.created_at
        
        # Determinar em qual hora (de Brasília) o gatilho ocorreu
        trigger_local = s.created_at - BRT_OFFSET
        trig_hour = trigger_local.hour
        
        # Simular apostas
        win = False
        gale_used = -1
        
        for g in range(payload.max_gales + 1):
            curr_idx = entry_idx + g
            if curr_idx >= num_spins:
                break
            curr_spin = spins[curr_idx]
            # Vitória se bater a cor de entrada OU Branco (proteção)
            if curr_spin.color == payload.entry_color or curr_spin.color == 0:
                win = True
                gale_used = g
                break
                
        # Atualiza a contagem daquela hora específica
        hourly_data[trig_hour]["total"] += 1
        if win:
            if gale_used == 0:
                hourly_data[trig_hour]["sg"] += 1
            elif gale_used == 1:
                hourly_data[trig_hour]["g1"] += 1
            elif gale_used == 2:
                hourly_data[trig_hour]["g2"] += 1
            elif gale_used == 3:
                hourly_data[trig_hour]["g3"] += 1
        else:
            hourly_data[trig_hour]["loss"] += 1
            
    # 3. Consolidar os dados gerais (overall) com base no filtro de horas
    sg = 0
    g1 = 0
    g2 = 0
    g3 = 0
    loss = 0
    total_signals = 0
    
    if payload.hour is not None:
        # Apenas os dados da hora solicitada
        h_data = hourly_data[payload.hour]
        sg = h_data["sg"]
        g1 = h_data["g1"]
        g2 = h_data["g2"]
        g3 = h_data["g3"]
        loss = h_data["loss"]
        total_signals = h_data["total"]
    else:
        # Soma todos as horas do dia
        for h in range(24):
            h_data = hourly_data[h]
            sg += h_data["sg"]
            g1 += h_data["g1"]
            g2 += h_data["g2"]
            g3 += h_data["g3"]
            loss += h_data["loss"]
            total_signals += h_data["total"]
            
    total_greens = sg + g1 + g2 + g3
    overall_win_rate = round((total_greens / total_signals * 100), 1) if total_signals > 0 else 0.0
    
    # 4. Formatar a resposta das 24 horas para o accordion
    hourly_response = {}
    for h in range(24):
        h_data = hourly_data[h]
        h_total = h_data["total"]
        h_greens = h_data["sg"] + h_data["g1"] + h_data["g2"] + h_data["g3"]
        h_win_rate = round((h_greens / h_total * 100), 1) if h_total > 0 else 0.0
        hourly_response[h] = {
            "win_rate": h_win_rate,
            "total_signals": h_total
        }
        
    return {
        "success": True,
        "win_rate": overall_win_rate,
        "total_signals": total_signals,
        "sg": sg,
        "g1": g1,
        "g2": g2,
        "g3": g3,
        "loss": loss,
        "hourly": hourly_response
    }


# --- ROTA DE WEBSOCKET EM TEMPO REAL ---

# Nota: Declarado fora do router global para podermos gerenciar o middleware de autenticação 
# de forma independente por conta da natureza persistente da conexão WS.
websocket_router = APIRouter()

@websocket_router.websocket("/ws/live")
async def websocket_endpoint(
    websocket: WebSocket,
    api_key: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """
    WebSocket em tempo real que transmite novos giros da Blaze Double.
    A autenticação exige a query string 'api_key'.
    """
    # 1. Autenticação na Conexão Inicial
    try:
        await verify_api_key(api_key=api_key, db=db)
    except HTTPException as e:
        # Abre e fecha a conexão com código de erro de política caso inválida
        await websocket.accept()
        await websocket.send_json({"error": "Unauthorized", "detail": str(e.detail)})
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    # 2. Registro da conexão ativa
    await manager.connect(websocket)
    try:
        while True:
            # Mantém a conexão aberta escutando batidas do cliente (se houver)
            await websocket.receive_text()
    except WebSocketDisconnect:
        await manager.disconnect(websocket)
