import plotly.graph_objects as go

def plot_radar(criteria_dict):

    labels = ["Tendência", "Momentum", "Volatilidade", "Sinal Técnico", "Volume"]

    values = [
        float(criteria_dict["tendencia"]["norm"]),
        float(criteria_dict["momentum"]["norm"]),
        float(criteria_dict["volatilidade"]["norm"]),
        float(criteria_dict["sinal_tecnico"]["norm"]),
        float(criteria_dict["volume"]["norm"]),
    ]

    values += values[:1]  # fecha o radar

    fig = go.Figure()

    fig.add_trace(go.Scatterpolar(
        r=values,
        theta=labels + [labels[0]],
        fill='toself',
        fillcolor='rgba(46, 123, 255, 0.25)',   # preenchimento premium
        line=dict(
            color='rgba(46, 123, 255, 1)',
            width=3
        ),
        hovertemplate="<b>%{theta}</b><br>Valor normalizado: %{r:.2f}<extra></extra>"
    ))

    fig.update_layout(
        polar=dict(
            bgcolor="#0E1117",
            radialaxis=dict(
                visible=True,
                color="rgba(200,200,200,0.15)",
                gridcolor="rgba(255,255,255,0.08)",
                showticklabels=False,
                range=[0, 1],
            ),
            angularaxis=dict(
                tickfont=dict(size=10, color="#CCCCCC"),
                gridcolor="rgba(255,255,255,0.08)",
            )
        ),
        showlegend=False,
        paper_bgcolor="#0E1117",
        margin=dict(l=0, r=0, t=0, b=0),

        # Radar compacto e elegante
        height=280,
    )

    return fig
