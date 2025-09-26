import os
import sqlite3
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QCheckBox, QScrollArea, QFrame, QLabel, QLineEdit, QHeaderView,
    QMessageBox, QTabWidget, QGraphicsView, QGraphicsScene
)
from PyQt6.QtGui import QPainter, QPen, QIntValidator, QFont
from PyQt6.QtCore import Qt, QEvent

# Definiši putanju do baze
DB_PATH = "data/baza.db"


# --- POMOĆNE KLASE ---

class UppercaseLineEdit(QLineEdit):
    """Custom klasa za unos teksta koji se automatski konvertuje u velika slova."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.textChanged.connect(self.to_uppercase)

    def to_uppercase(self):
        self.blockSignals(True)
        self.setText(self.text().upper())
        self.blockSignals(False)


# --- GLAVNA APLIKACIJA ---

class SimpleApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Turnusi_VV")
        self.resize(1400, 900)
        self.init_database()

        # Promenljive za režim uređivanja
        self.trenutni_broj_za_izmenu = None
        self.trenutni_turnus_za_izmenu = None

        # Informacije o sortiranju
        self.vozi_sort_info = {'column': 0, 'order': Qt.SortOrder.AscendingOrder}  # Default: broj voza ASC
        self.turnusi_sort_info = {'column': 0, 'order': Qt.SortOrder.AscendingOrder}  # Default: naziv ASC

        # Informacije o grafiku
        self.godina_za_grafik = ""  # Atribut za čuvanje unete godine

        # Inicijalizuj self.godina_input odmah da bi bio dostupan svim tabovima
        # Proveri da li već postoji iz init_database (sigurnosna mera)
        if not hasattr(self, 'godina_input') or self.godina_input is None:
            self.godina_input = QLineEdit()
            self.godina_input.setPlaceholderText("Npr. 09.12.2025/26")
            self.godina_input.setText(self.godina_za_grafik) # Ovo se radi u ucitaj_godinu_za_grafik
            # self.godina_input.setText(self.godina_za_grafik) # Ovo se radi u ucitaj_godinu_za_grafik
            self.godina_input.textChanged.connect(self.snimi_godinu_za_grafik)

        # Inicijalizacija UI - OVO MORA BITI PRE populate_filters_and_load_data
        self.init_ui()

        # Popunjavanje filtera i učitavanje podataka - OVO IDE POSLE init_ui
        self.populate_filters_and_load_data()

    def populate_filters_and_load_data(self):
        """Centralizovana funkcija za popunjavanje svih filtera i učitavanje početnih podataka."""
        # Tab Vozovi
        self.populate_vozovi_filter()
        self.populate_sekcije_filter()
        self.populate_serije_filter()
        self.ucitaj_podatke(sort_column=None, sort_order=None)  # Inicijalno bez sortiranja

        # Tab Turnusi
        self.populate_nazivi_filter()
        self.populate_sekcije_turnusi_filter()
        self.populate_serije_vv_filter()
        self.ucitaj_turnuse(sort_column=None, sort_order=None)  # Inicijalno bez sortiranja

        # Tab Grafik
        self.populate_grafik_filter()

    # --- BAZA PODATAKA ---

    def init_database(self):
        """Inicijalizuje bazu podataka i tabele."""
        os.makedirs("data", exist_ok=True)
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Tabela za vozove
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS vozovi (
                broj_voza TEXT PRIMARY KEY,
                pocetna_stanica TEXT,
                krajnja_stanica TEXT,
                sat_polaska INTEGER,
                minut_polaska INTEGER,
                sat_dolaska INTEGER,
                minut_dolaska INTEGER,
                status TEXT,
                sekcija TEXT,
                serija_vozila TEXT
            )
        ''')

        # Tabela za turnuse
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS turnusi (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                naziv TEXT UNIQUE,
                sekcija TEXT,
                serija_vv TEXT
            )
        ''')

        # Tabela za veze između turnusa i voza
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS turnus_vozovi (
                turnus_id INTEGER,
                broj_voza TEXT,
                redosled INTEGER,
                PRIMARY KEY (turnus_id, broj_voza),
                FOREIGN KEY (turnus_id) REFERENCES turnusi(id),
                FOREIGN KEY (broj_voza) REFERENCES vozovi(broj_voza)
            )
        ''')
        conn.commit()
        conn.close()

        # --- UKLONJENO ---
        # # Učitaj prethodno sačuvanu godinu prilikom inicijalizacije baze
        self.ucitaj_godinu_za_grafik()
        # self.ucitaj_godinu_za_grafik()
        # ---

    # --- KORISNIČKI INTERFEJS ---
    def init_ui(self):
        """Inicijalizuje korisnički interfejs sa tabovima."""
        main_layout = QVBoxLayout()
        self.tabs = QTabWidget()
        self.tabs.addTab(self.create_tab_vozovi(), "Vozovi")
        self.tabs.addTab(self.create_tab_turnusi(), "Turnusi")
        self.tabs.addTab(self.create_tab_grafik(), "Pregled Grafika")
        # DODAVANJE NOVOG TABA
        self.tabs.addTab(self.create_tab_stampa(), "Stampa turnusa")
        main_layout.addWidget(self.tabs)
        self.setLayout(main_layout)

    def create_tab_vozovi(self):
        """Kreira tab za upravljanje vozovima."""
        widget = QWidget()
        main_layout = QVBoxLayout()

        # --- GORNJI DEO (30%) ---
        top_frame = QFrame()
        top_frame.setFrameShape(QFrame.Shape.StyledPanel)
        top_layout = QHBoxLayout(top_frame)

        # === Forma za unos voza (55%) ===
        left_frame = QFrame()
        left_frame.setFrameShape(QFrame.Shape.StyledPanel)
        left_layout = QVBoxLayout(left_frame)
        naslov = QLabel("Unos voza")
        naslov.setStyleSheet("font-size: 16px; font-weight: bold;")
        left_layout.addWidget(naslov)

        # Input polja
        self.broj_voza_input = UppercaseLineEdit()
        self.pocetna_input = UppercaseLineEdit()
        self.krajnja_input = UppercaseLineEdit()
        self.sat_p_input = UppercaseLineEdit()
        self.minut_p_input = UppercaseLineEdit()
        self.sat_d_input = UppercaseLineEdit()
        self.minut_d_input = UppercaseLineEdit()
        self.serija_input = UppercaseLineEdit()
        self.status_input = UppercaseLineEdit()
        self.sekcija_input = UppercaseLineEdit()

        # Validatori
        self.sat_p_input.setValidator(QIntValidator(0, 23))
        self.minut_p_input.setValidator(QIntValidator(0, 59))
        self.sat_d_input.setValidator(QIntValidator(0, 23))
        self.minut_d_input.setValidator(QIntValidator(0, 59))

        # Layout forme
        form_inner = QHBoxLayout()
        levo_forme = QVBoxLayout()
        desno_forme = QVBoxLayout()

        levo_forme.addWidget(QLabel("Broj voza (3-6 alfanumerička znaka, npr. R4655):"))
        levo_forme.addWidget(self.broj_voza_input)
        levo_forme.addWidget(QLabel("Početna stanica (2-3 slova):"))
        levo_forme.addWidget(self.pocetna_input)
        levo_forme.addWidget(QLabel("Krajnja stanica (2-3 slova):"))
        levo_forme.addWidget(self.krajnja_input)
        levo_forme.addWidget(QLabel("Sat polaska (hh):"))
        levo_forme.addWidget(self.sat_p_input)
        levo_forme.addWidget(QLabel("Minut polaska (mm):"))
        levo_forme.addWidget(self.minut_p_input)

        desno_forme.addWidget(QLabel("Sat dolaska (hh):"))
        desno_forme.addWidget(self.sat_d_input)
        desno_forme.addWidget(QLabel("Minut dolaska (mm):"))
        desno_forme.addWidget(self.minut_d_input)
        desno_forme.addWidget(QLabel("Serija vučnog vozila:"))
        desno_forme.addWidget(self.serija_input)
        desno_forme.addWidget(QLabel("Status (R, L, RE, S, V):"))
        desno_forme.addWidget(self.status_input)
        desno_forme.addWidget(QLabel("Sekcija (npr. KV):"))
        desno_forme.addWidget(self.sekcija_input)

        form_inner.addLayout(levo_forme)
        form_inner.addLayout(desno_forme)
        left_layout.addLayout(form_inner)

        # Dugmad
        btn_layout = QHBoxLayout()
        self.btn_dodaj = QPushButton("Dodaj voz")
        self.btn_dodaj.clicked.connect(self.dodaj_voz)
        self.btn_azuriraj = QPushButton("Ažuriraj voz")
        self.btn_azuriraj.clicked.connect(self.azuriraj_voz)
        self.btn_azuriraj.setVisible(False)
        self.btn_odustani = QPushButton("Odustani od uređivanja")
        self.btn_odustani.clicked.connect(self.odustani_od_uredjivanja)
        self.btn_odustani.setVisible(False)
        btn_layout.addWidget(self.btn_dodaj)
        btn_layout.addWidget(self.btn_azuriraj)
        btn_layout.addWidget(self.btn_odustani)
        left_layout.addLayout(btn_layout)
        top_layout.addWidget(left_frame, 55)

        # === Filteri ===
        # Filter po vozovima (15%)
        center_frame = QFrame()
        center_frame.setFrameShape(QFrame.Shape.StyledPanel)
        center_layout = QVBoxLayout(center_frame)
        label_voz = QLabel("Filter po vozovima:")
        center_layout.addWidget(label_voz)
        self.voz_filter_widget = QWidget()
        self.voz_filter_layout = QVBoxLayout()
        self.voz_filter_layout.setSpacing(2)
        self.all_vozovi_cb = QCheckBox("Označi sve")
        self.all_vozovi_cb.setChecked(True)
        self.all_vozovi_cb.stateChanged.connect(self.on_all_vozovi_toggled)
        self.voz_filter_layout.addWidget(self.all_vozovi_cb)
        self.voz_filter_widget.setLayout(self.voz_filter_layout)
        scroll_voz = QScrollArea()
        scroll_voz.setWidgetResizable(True)
        scroll_voz.setWidget(self.voz_filter_widget)
        center_layout.addWidget(scroll_voz)
        top_layout.addWidget(center_frame, 15)

        # Filter po sekcijama (15%)
        right_frame = QFrame()
        right_frame.setFrameShape(QFrame.Shape.StyledPanel)
        right_layout = QVBoxLayout(right_frame)
        label_sekcija = QLabel("Filter po sekciji:")
        right_layout.addWidget(label_sekcija)
        self.sekcije_filter_widget = QWidget()
        self.sekcije_filter_layout = QVBoxLayout()
        self.sekcije_filter_layout.setSpacing(2)
        self.all_sekcije_cb = QCheckBox("Označi sve")
        self.all_sekcije_cb.setChecked(True)
        self.all_sekcije_cb.stateChanged.connect(self.on_all_sekcije_toggled)
        self.sekcije_filter_layout.addWidget(self.all_sekcije_cb)
        self.sekcije_filter_widget.setLayout(self.sekcije_filter_layout)
        scroll_sekcija = QScrollArea()
        scroll_sekcija.setWidgetResizable(True)
        scroll_sekcija.setWidget(self.sekcije_filter_widget)
        right_layout.addWidget(scroll_sekcija)
        top_layout.addWidget(right_frame, 15)

        # Filter po serijama (15%)
        serija_frame = QFrame()
        serija_frame.setFrameShape(QFrame.Shape.StyledPanel)
        serija_layout = QVBoxLayout(serija_frame)
        label_serija = QLabel("Filter po seriji:")
        serija_layout.addWidget(label_serija)
        self.serije_filter_widget = QWidget()
        self.serije_filter_layout = QVBoxLayout()
        self.serije_filter_layout.setSpacing(2)
        self.all_serije_cb = QCheckBox("Označi sve")
        self.all_serije_cb.setChecked(True)
        self.all_serije_cb.stateChanged.connect(self.on_all_serije_toggled)
        self.serije_filter_layout.addWidget(self.all_serije_cb)
        self.serije_filter_widget.setLayout(self.serije_filter_layout)
        scroll_serija = QScrollArea()
        scroll_serija.setWidgetResizable(True)
        scroll_serija.setWidget(self.serije_filter_widget)
        serija_layout.addWidget(scroll_serija)
        top_layout.addWidget(serija_frame, 15)

        main_layout.addWidget(top_frame, 30)

        # --- DONJI DEO (70%) ---
        bottom_frame = QFrame()
        bottom_frame.setFrameShape(QFrame.Shape.StyledPanel)
        bottom_layout = QVBoxLayout(bottom_frame)
        bottom_layout.addWidget(QLabel("Postojeći vozovi:"))
        self.tabela = QTableWidget()
        self.tabela.setColumnCount(10)
        self.tabela.setHorizontalHeaderLabels([
            "Broj voza", "Poč. st.", "Kraj. st.", "Polazak", "Dolazak",
            "Serija", "Status", "Sekcija", "Uredi", "Obriši"
        ])
        self.tabela.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        # ONEMOGUĆI Qt SORTIRANJE
        self.tabela.setSortingEnabled(False)

        # Poveži klik na zaglavlje sa funkcijom za rukovanje sortiranjem
        self.tabela.horizontalHeader().sectionClicked.connect(self.handle_vozovi_header_click)

        bottom_layout.addWidget(self.tabela)
        main_layout.addWidget(bottom_frame, 70)

        widget.setLayout(main_layout)
        return widget

    def create_tab_turnusi(self):
        """Kreira tab za upravljanje turnusima."""
        widget = QWidget()
        main_layout = QVBoxLayout()

        # --- GORNJI DEO (30%) ---
        top_frame = QFrame()
        top_frame.setFrameShape(QFrame.Shape.StyledPanel)
        top_layout = QHBoxLayout(top_frame)

        # === Forma za unos turnusa (55%) ===
        left_frame = QFrame()
        left_frame.setFrameShape(QFrame.Shape.StyledPanel)
        left_layout = QVBoxLayout(left_frame)
        naslov = QLabel("Unos turnusa")
        naslov.setStyleSheet("font-size: 16px; font-weight: bold;")
        left_layout.addWidget(naslov)

        # Polja forme
        self.naziv_turnusa_input = QLineEdit()
        self.naziv_turnusa_input.setPlaceholderText("Npr. TUR1")
        self.serija_vv_input = UppercaseLineEdit()
        self.serija_vv_input.setPlaceholderText("Npr. 441, 442")
        self.vozovi_input = QLineEdit()
        self.vozovi_input.setPlaceholderText("Npr. 4830, 4831, 4832")
        self.sekcija_voza_input = UppercaseLineEdit()
        self.sekcija_voza_input.setPlaceholderText("Npr. KV")

        left_layout.addWidget(QLabel("Naziv turnusa:"))
        left_layout.addWidget(self.naziv_turnusa_input)
        left_layout.addWidget(QLabel("Serija VV:"))
        left_layout.addWidget(self.serija_vv_input)
        left_layout.addWidget(QLabel("Vozovi u turnusu:"))
        left_layout.addWidget(self.vozovi_input)
        left_layout.addWidget(QLabel("Sekcija za vuču vozova:"))
        left_layout.addWidget(self.sekcija_voza_input)

        # Dugmad
        self.btn_proveri = QPushButton("Proveri turnus")
        self.btn_proveri.clicked.connect(self.proveri_turnus)
        left_layout.addWidget(self.btn_proveri)
        self.btn_odustani_turnus = QPushButton("Odustani od uređivanja")
        self.btn_odustani_turnus.clicked.connect(self.odustani_od_uredjivanja_turnusa)
        self.btn_odustani_turnus.setVisible(False)
        left_layout.addWidget(self.btn_odustani_turnus)

        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet("padding: 10px; background-color: #f0f0f0; border-radius: 5px;")
        left_layout.addWidget(self.status_label)
        top_layout.addWidget(left_frame, 55)

        # === Filteri ===
        # Filter po nazivu (15%)
        center_frame = QFrame()
        center_frame.setFrameShape(QFrame.Shape.StyledPanel)
        center_layout = QVBoxLayout(center_frame)
        label_naziv = QLabel("Filter po nazivu:")
        center_layout.addWidget(label_naziv)
        self.naziv_filter_widget = QWidget()
        self.naziv_filter_layout = QVBoxLayout()
        self.naziv_filter_layout.setSpacing(2)
        self.all_nazivi_cb = QCheckBox("Označi sve")
        self.all_nazivi_cb.setChecked(True)
        self.all_nazivi_cb.stateChanged.connect(self.on_all_nazivi_toggled)
        self.naziv_filter_layout.addWidget(self.all_nazivi_cb)
        self.naziv_filter_widget.setLayout(self.naziv_filter_layout)
        scroll_naziv = QScrollArea()
        scroll_naziv.setWidgetResizable(True)
        scroll_naziv.setWidget(self.naziv_filter_widget)
        center_layout.addWidget(scroll_naziv)
        top_layout.addWidget(center_frame, 15)

        # Filter po sekciji (15%)
        right_frame = QFrame()
        right_frame.setFrameShape(QFrame.Shape.StyledPanel)
        right_layout = QVBoxLayout(right_frame)
        label_sekcija = QLabel("Filter po sekciji:")
        right_layout.addWidget(label_sekcija)
        self.sekcije_turnusi_filter_widget = QWidget()
        self.sekcije_turnusi_filter_layout = QVBoxLayout()
        self.sekcije_turnusi_filter_layout.setSpacing(2)
        self.all_sekcije_turnusi_cb = QCheckBox("Označi sve")
        self.all_sekcije_turnusi_cb.setChecked(True)
        self.all_sekcije_turnusi_cb.stateChanged.connect(self.on_all_sekcije_turnusi_toggled)
        self.sekcije_turnusi_filter_layout.addWidget(self.all_sekcije_turnusi_cb)
        self.sekcije_turnusi_filter_widget.setLayout(self.sekcije_turnusi_filter_layout)
        scroll_sekcija = QScrollArea()
        scroll_sekcija.setWidgetResizable(True)
        scroll_sekcija.setWidget(self.sekcije_turnusi_filter_widget)
        right_layout.addWidget(scroll_sekcija)
        top_layout.addWidget(right_frame, 15)

        # Filter po seriji VV (15%)
        serija_frame = QFrame()
        serija_frame.setFrameShape(QFrame.Shape.StyledPanel)
        serija_layout = QVBoxLayout(serija_frame)
        label_serija = QLabel("Filter po seriji VV:")
        serija_layout.addWidget(label_serija)
        self.serije_vv_filter_widget = QWidget()
        self.serije_vv_filter_layout = QVBoxLayout()
        self.serije_vv_filter_layout.setSpacing(2)
        self.all_serije_vv_cb = QCheckBox("Označi sve")
        self.all_serije_vv_cb.setChecked(True)
        self.all_serije_vv_cb.stateChanged.connect(self.on_all_serije_vv_toggled)
        self.serije_vv_filter_layout.addWidget(self.all_serije_vv_cb)
        self.serije_vv_filter_widget.setLayout(self.serije_vv_filter_layout)
        scroll_serija = QScrollArea()
        scroll_serija.setWidgetResizable(True)
        scroll_serija.setWidget(self.serije_vv_filter_widget)
        serija_layout.addWidget(scroll_serija)
        top_layout.addWidget(serija_frame, 15)

        main_layout.addWidget(top_frame, 30)

        # --- DONJI DEO (70%) ---
        bottom_frame = QFrame()
        bottom_frame.setFrameShape(QFrame.Shape.StyledPanel)
        bottom_layout = QVBoxLayout(bottom_frame)
        bottom_layout.addWidget(QLabel("Postojeći turnusi:"))
        self.tabela_turnusa = QTableWidget()
        self.tabela_turnusa.setColumnCount(5)
        self.tabela_turnusa.setHorizontalHeaderLabels([
            "Naziv", "Serija VV", "Vozovi", "Sekcija", "Akcije"
        ])
        self.tabela_turnusa.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        # ONEMOGUĆI Qt SORTIRANJE
        self.tabela_turnusa.setSortingEnabled(False)

        # Poveži klik na zaglavlje sa funkcijom za rukovanje sortiranjem
        self.tabela_turnusa.horizontalHeader().sectionClicked.connect(self.handle_turnusi_header_click)

        bottom_layout.addWidget(self.tabela_turnusa)
        main_layout.addWidget(bottom_frame, 70)

        widget.setLayout(main_layout)
        return widget

    def create_tab_grafik(self):
        """Kreira tab za grafički prikaz turnusa."""
        widget = QWidget()
        main_layout = QVBoxLayout()

        # --- GORNJI DEO (30%) ---
        top_frame = QFrame()
        top_frame.setFrameShape(QFrame.Shape.StyledPanel)
        top_layout = QHBoxLayout(top_frame)

        # === Filteri za grafik ===
        # Filter po turnusima (25%)
        left_frame = QFrame()
        left_frame.setFrameShape(QFrame.Shape.StyledPanel)
        left_layout = QVBoxLayout(left_frame)
        label_turnusi = QLabel("Izaberite turnuse za prikaz:")
        left_layout.addWidget(label_turnusi)
        self.grafik_filter_widget = QWidget()
        self.grafik_filter_layout = QVBoxLayout()
        self.grafik_filter_layout.setSpacing(2)
        self.all_turnusi_cb = QCheckBox("Označi sve")
        self.all_turnusi_cb.setChecked(True)
        self.all_turnusi_cb.stateChanged.connect(self.on_all_turnusi_toggled)
        self.grafik_filter_layout.addWidget(self.all_turnusi_cb)
        self.grafik_filter_widget.setLayout(self.grafik_filter_layout)
        scroll_turnusi = QScrollArea()
        scroll_turnusi.setWidgetResizable(True)
        scroll_turnusi.setWidget(self.grafik_filter_widget)
        left_layout.addWidget(scroll_turnusi)
        top_layout.addWidget(left_frame, 25)

        # Filter po sekcijama (25%)
        center_frame = QFrame()
        center_frame.setFrameShape(QFrame.Shape.StyledPanel)
        center_layout = QVBoxLayout(center_frame)
        label_sekcije = QLabel("Filter po sekcijama:")
        center_layout.addWidget(label_sekcije)
        self.sekcije_grafik_widget = QWidget()
        self.sekcije_grafik_layout = QVBoxLayout()
        self.sekcije_grafik_layout.setSpacing(2)
        self.all_sekcije_grafik_cb = QCheckBox("Označi sve")
        self.all_sekcije_grafik_cb.setChecked(True)
        self.all_sekcije_grafik_cb.stateChanged.connect(self.on_all_sekcije_grafik_toggled)
        self.sekcije_grafik_layout.addWidget(self.all_sekcije_grafik_cb)
        self.sekcije_grafik_widget.setLayout(self.sekcije_grafik_layout)
        scroll_sekcije = QScrollArea()
        scroll_sekcije.setWidgetResizable(True)
        scroll_sekcije.setWidget(self.sekcije_grafik_widget)
        center_layout.addWidget(scroll_sekcije)
        top_layout.addWidget(center_frame, 25)

        # Filter po seriji VV (25%)
        right_frame = QFrame()
        right_frame.setFrameShape(QFrame.Shape.StyledPanel)
        right_layout = QVBoxLayout(right_frame)
        label_serije_vv = QLabel("Filter po seriji VV:")
        right_layout.addWidget(label_serije_vv)
        self.serije_vv_grafik_widget = QWidget()
        self.serije_vv_grafik_layout = QVBoxLayout()
        self.serije_vv_grafik_layout.setSpacing(2)
        self.all_serije_vv_grafik_cb = QCheckBox("Označi sve")
        self.all_serije_vv_grafik_cb.setChecked(True)
        self.all_serije_vv_grafik_cb.stateChanged.connect(self.on_all_serije_vv_grafik_toggled)
        self.serije_vv_grafik_layout.addWidget(self.all_serije_vv_grafik_cb)
        self.serije_vv_grafik_widget.setLayout(self.serije_vv_grafik_layout)
        scroll_serije_vv = QScrollArea()
        scroll_serije_vv.setWidgetResizable(True)
        scroll_serije_vv.setWidget(self.serije_vv_grafik_widget)
        right_layout.addWidget(scroll_serije_vv)
        top_layout.addWidget(right_frame, 25)

        # === Prosireni turnus (25%) ===
        empty_frame = QFrame()
        empty_frame.setFrameShape(QFrame.Shape.StyledPanel)
        empty_layout = QVBoxLayout(empty_frame)

        # Naslov forme
        naslov_prosireni_label = QLabel("Prosireni turnus")
        naslov_prosireni_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        naslov_prosireni_label.setStyleSheet("font-weight: bold;")
        empty_layout.addWidget(naslov_prosireni_label)

        # Tekst uputstva
        uputstvo_label = QLabel("Uneti naziv prosirenog turnusa:")
        empty_layout.addWidget(uputstvo_label)

        # QLineEdit za unos naziva
        self.naziv_prosirenog_input = QLineEdit()
        self.naziv_prosirenog_input.setPlaceholderText("Npr. TUR01")
        empty_layout.addWidget(self.naziv_prosirenog_input)

        # QPushButton za prikaz
        self.btn_prikazi_prosireni = QPushButton("Prikazi prosireni turnus")
        # TODO: Povezati sa odgovarajucom funkcijom
        self.btn_prikazi_prosireni.clicked.connect(self.prikazi_prosireni_turnus)  # <- DODATO
        # self.btn_prikazi_prosireni.clicked.connect(self.prikazi_prosireni_turnus)
        empty_layout.addWidget(self.btn_prikazi_prosireni)

        top_layout.addWidget(empty_frame, 25)

        main_layout.addWidget(top_frame, 30)

        # --- DONJI DEO (70%) ---
        bottom_frame = QFrame()
        bottom_frame.setFrameShape(QFrame.Shape.StyledPanel)
        bottom_layout = QVBoxLayout(bottom_frame)
        naslov = QLabel("Grafički prikaz turnusa")
        naslov.setStyleSheet("font-size: 16px; font-weight: bold;")
        bottom_layout.addWidget(naslov)
        self.scene = QGraphicsScene()
        self.view = QGraphicsView(self.scene)
        self.view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        bottom_layout.addWidget(self.view)
        self.btn_azuriraj_grafik = QPushButton("Ažuriraj grafik")
        self.btn_azuriraj_grafik.clicked.connect(self.crtaj_grafik)
        bottom_layout.addWidget(self.btn_azuriraj_grafik)
        main_layout.addWidget(bottom_frame, 70)

        widget.setLayout(main_layout)
        return widget

    def create_tab_stampa(self):
        """Kreira tab za prikaz i štampu turnusa."""
        widget = QWidget()
        main_layout = QVBoxLayout()

        # --- GORNJI DEO (25%) ---
        top_frame = QFrame()
        top_frame.setFrameShape(QFrame.Shape.StyledPanel)
        top_layout = QHBoxLayout(top_frame)

        # === Kontrole za izbor turnusa (33.33%) ===
        left_top_frame = QFrame()
        left_top_frame.setFrameShape(QFrame.Shape.StyledPanel)
        left_top_layout = QVBoxLayout(left_top_frame)
        left_top_layout.addWidget(QLabel("Kontrole za izbor turnusa"))
        # TODO: Dodati kontrole za izbor sekcije, filtriranje turnusa itd.
        # Za sada je prazan placeholder
        left_top_layout.addStretch()
        top_layout.addWidget(left_top_frame, 33)  # 33% širine

        # === Pregled selekcije (33.33%) ===
        middle_top_frame = QFrame()
        middle_top_frame.setFrameShape(QFrame.Shape.StyledPanel)
        middle_top_layout = QVBoxLayout(middle_top_frame)
        middle_top_layout.addWidget(QLabel("Pregled selekcije"))
        # TODO: Dodati widget za prikaz izabranih turnusa
        # Za sada je prazan placeholder
        middle_top_layout.addStretch()
        top_layout.addWidget(middle_top_frame, 33)  # 33% širine

        # === GRAFIČKI TURNUS VUČNIH VOZILA ZA RED VOŽNJE (33.33%) ===
        right_top_frame = QFrame()
        right_top_frame.setFrameShape(QFrame.Shape.StyledPanel)
        right_top_layout = QVBoxLayout(right_top_frame)  # Koristi QVBoxLayout za vertikalni raspored

        # Naslov
        naslov_label = QLabel("GRAFIČKI TURNUS VUČNIH VOZILA ZA RED VOŽNJE")
        naslov_label.setAlignment(Qt.AlignmentFlag.AlignCenter)  # Centriraj tekst
        naslov_label.setStyleSheet("font-weight: bold;")  # Opcionalno: podebljaj tekst
        right_top_layout.addWidget(naslov_label)

        # Horizontalni layout za input i label "GODINU"
        input_layout = QHBoxLayout()
        input_layout.addStretch()  # Dodaj fleksibilni prostor levo

        # QLineEdit za unos godine - KORISTIMO ISTU INSTANCU KAO I ZA GRAFIK
        # Proveravamo da li self.godina_input već postoji (iz create_tab_grafik)
        # Ako ne postoji, kreiraćemo je ovde, ali bolje je da postoji iz create_tab_grafik
        # Pretpostavimo da self.godina_input postoji. Ako ne, dodajemo sigurnosnu mreu.
        if not hasattr(self, 'godina_input') or self.godina_input is None:
            # Sigurnosna mera ako nije inicijalizovana ranije (npr. ako se tab "Stampa" kreira pre "Grafik")
            self.godina_input = QLineEdit()
            self.godina_input.setPlaceholderText("Npr. 09.12.2025/26")
            self.godina_input.setText(self.godina_za_grafik) # Ovo se poziva u ucitaj_godinu_za_grafik
            # self.godina_input.setText(self.godina_za_grafik) # Ovo se poziva u ucitaj_godinu_za_grafik
            self.godina_input.textChanged.connect(self.snimi_godinu_za_grafik)

        # PODEBLJAJ FONT I CENTRIRAJ TEKST U QLineEdit
        font_le = self.godina_input.font()
        font_le.setBold(True)
        self.godina_input.setFont(font_le)
        self.godina_input.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # UCITAJ VREDNOST IZ FAJLA (ako vec nije ucitana u init_database ili create_tab_grafik)
        # Ovo bi trebalo da se desi jednom pri inicijalizaciji, ali za svaki slucaj proverimo
        self.ucitaj_godinu_za_grafik() # Ovo vec treba da je pozvano u init_database
        # self.ucitaj_godinu_za_grafik() # Ovo vec treba da je pozvano u init_database
        # Ako nije, mozemo ga pozvati ovde, ali bolje je osigurati da se u init_database pozove jednom
        # i da self.godina_za_grafik bude inicijalizovan

        input_layout.addWidget(self.godina_input)
        input_layout.addStretch()  # Dodaj fleksibilni prostor desno
        right_top_layout.addLayout(input_layout)  # Dodaj horizontalni layout

        # QLabel "GODINU" ISPOT QLineEdiTA - PODEBLJAJ I CENTRIRAJ
        label_godina = QLabel("GODINU")
        label_godina.setAlignment(Qt.AlignmentFlag.AlignCenter)  # Centriraj tekst
        label_godina.setStyleSheet("font-weight: bold;")  # Podebljaj tekst
        right_top_layout.addWidget(label_godina)  # Dodaj ispod inputa

        top_layout.addWidget(right_top_frame, 34)  # 34% širine (zaokruženo)

        main_layout.addWidget(top_frame, 25)  # 25% visine

        # --- DONJI DEO (75%) ---
        bottom_frame = QFrame()
        bottom_frame.setFrameShape(QFrame.Shape.StyledPanel)
        bottom_layout = QVBoxLayout(bottom_frame)
        bottom_layout.addWidget(QLabel("Prikaz za štampu (A4 format) - 100% širine donjeg dela"))

        # TODO: Dodati QGraphicsView ili drugi widget za prikaz A4
        self.stampa_scene = QGraphicsScene()
        self.stampa_view = QGraphicsView(self.stampa_scene)
        self.stampa_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        # Postaviti fiksnu veličinu za A4 (210mm x 297mm) na ekranu
        # Primer: 1mm = 3.78 px na ekranu (96 DPI), pa je A4 ~ 794 x 1123 px
        # self.stampa_view.setFixedSize(794, 1123) # Ako želiš fiksnu veličinu
        bottom_layout.addWidget(self.stampa_view)

        main_layout.addWidget(bottom_frame, 75)  # 75% visine

        widget.setLayout(main_layout)
        return widget

    # --- FUNKCIJE ZA FILTRIRANJE (CHECKBOX KONTROLE) ---
    def on_individual_checkbox_changed(self, state, checkbox, all_checkbox, reload_function):
        """Kada se promeni individualni checkbox, ažuriraj 'Označi sve' i osveži prikaz."""
        # Ako je neki checkbox ručno rasčekiran, rasčekiraj "Označi sve"
        if state == Qt.CheckState.Unchecked.value:
            all_checkbox.blockSignals(True)
            all_checkbox.setChecked(False)
            all_checkbox.blockSignals(False)
        # Ako su svi checkboxovi čekirani, čekiraj "Označi sve"
        # Pronađi sve checkboxove u istom layoutu (osim "Označi sve")
        layout = checkbox.parentWidget().layout()
        all_checked = True
        for i in range(1, layout.count()):  # Počinjemo od 1 da preskočimo "Označi sve"
            w = layout.itemAt(i).widget()
            if isinstance(w, QCheckBox) and not w.isChecked():
                all_checked = False
                break

        if all_checked and layout.count() > 1:  # Proveri da li postoji bar jedan checkbox osim "Označi sve"
            all_checkbox.blockSignals(True)
            all_checkbox.setChecked(True)
            all_checkbox.blockSignals(False)

        reload_function()

    def on_all_vozovi_toggled(self, state):
        is_checked = state == Qt.CheckState.Checked.value
        for i in range(self.voz_filter_layout.count()):
            widget = self.voz_filter_layout.itemAt(i).widget()
            if isinstance(widget, QCheckBox) and widget != self.all_vozovi_cb:
                widget.blockSignals(True)
                widget.setChecked(is_checked)
                widget.blockSignals(False)
        # Osveži bez sortiranja
        self.ucitaj_podatke(sort_column=None, sort_order=None)

    def on_all_sekcije_toggled(self, state):
        is_checked = state == Qt.CheckState.Checked.value
        for i in range(self.sekcije_filter_layout.count()):
            widget = self.sekcije_filter_layout.itemAt(i).widget()
            if isinstance(widget, QCheckBox) and widget != self.all_sekcije_cb:
                widget.blockSignals(True)
                widget.setChecked(is_checked)
                widget.blockSignals(False)
        # Osveži bez sortiranja
        self.ucitaj_podatke(sort_column=None, sort_order=None)

    def on_all_serije_toggled(self, state):
        is_checked = state == Qt.CheckState.Checked.value
        for i in range(1, self.serije_filter_layout.count()):
            widget = self.serije_filter_layout.itemAt(i).widget()
            if isinstance(widget, QCheckBox):
                widget.blockSignals(True)
                widget.setChecked(is_checked)
                widget.blockSignals(False)
        # Osveži bez sortiranja
        self.ucitaj_podatke(sort_column=None, sort_order=None)

    def on_all_nazivi_toggled(self, state):
        is_checked = state == Qt.CheckState.Checked.value
        for i in range(self.naziv_filter_layout.count()):
            widget = self.naziv_filter_layout.itemAt(i).widget()
            if isinstance(widget, QCheckBox) and widget != self.all_nazivi_cb:
                widget.blockSignals(True)
                widget.setChecked(is_checked)
                widget.blockSignals(False)
        # Osveži bez sortiranja
        self.ucitaj_turnuse(sort_column=None, sort_order=None)

    def on_all_sekcije_turnusi_toggled(self, state):
        is_checked = state == Qt.CheckState.Checked.value
        for i in range(self.sekcije_turnusi_filter_layout.count()):
            widget = self.sekcije_turnusi_filter_layout.itemAt(i).widget()
            if isinstance(widget, QCheckBox) and widget != self.all_sekcije_turnusi_cb:
                widget.blockSignals(True)
                widget.setChecked(is_checked)
                widget.blockSignals(False)
        # Osveži bez sortiranja
        self.ucitaj_turnuse(sort_column=None, sort_order=None)

    def on_all_serije_vv_toggled(self, state):
        is_checked = state == Qt.CheckState.Checked.value
        for i in range(1, self.serije_vv_filter_layout.count()):
            widget = self.serije_vv_filter_layout.itemAt(i).widget()
            if isinstance(widget, QCheckBox):
                widget.blockSignals(True)
                widget.setChecked(is_checked)
                widget.blockSignals(False)
        # Osveži bez sortiranja
        self.ucitaj_turnuse(sort_column=None, sort_order=None)

    def on_all_turnusi_toggled(self, state):
        is_checked = state == Qt.CheckState.Checked.value
        for i in range(1, self.grafik_filter_layout.count()):
            widget = self.grafik_filter_layout.itemAt(i).widget()
            if isinstance(widget, QCheckBox):
                widget.blockSignals(True)
                widget.setChecked(is_checked)
                widget.blockSignals(False)
        self.crtaj_grafik()

    def on_all_sekcije_grafik_toggled(self, state):
        is_checked = state == Qt.CheckState.Checked.value
        for i in range(1, self.sekcije_grafik_layout.count()):
            widget = self.sekcije_grafik_layout.itemAt(i).widget()
            if isinstance(widget, QCheckBox):
                widget.blockSignals(True)
                widget.setChecked(is_checked)
                widget.blockSignals(False)
        self.filter_turnuse_po_sekciji()

    def on_all_serije_vv_grafik_toggled(self, state):
        is_checked = state == Qt.CheckState.Checked.value
        for i in range(1, self.serije_vv_grafik_layout.count()):
            widget = self.serije_vv_grafik_layout.itemAt(i).widget()
            if isinstance(widget, QCheckBox):
                widget.blockSignals(True)
                widget.setChecked(is_checked)
                widget.blockSignals(False)
        self.filter_turnuse_po_seriji_vv()

    # --- POPUNJAVANJE FILTARA ---

    def populate_vozovi_filter(self):
        """Popunjava filter za vozove u tabu 'Vozovi'."""
        for i in reversed(range(self.voz_filter_layout.count())):
            item = self.voz_filter_layout.itemAt(i)
            if item and item.widget() != self.all_vozovi_cb:
                widget = item.widget()
                if widget:
                    widget.deleteLater()

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT broj_voza FROM vozovi ORDER BY broj_voza")
        brojevi = [str(row[0]) for row in cursor.fetchall()]
        conn.close()

        for b in brojevi:
            cb = QCheckBox(b)
            cb.setChecked(True)
            cb.stateChanged.connect(
                lambda state, checkbox=cb: self.on_individual_checkbox_changed(
                    state, checkbox, self.all_vozovi_cb, lambda: self.ucitaj_podatke(sort_column=None, sort_order=None)
                )
            )
            self.voz_filter_layout.addWidget(cb)

    def populate_sekcije_filter(self):
        """Popunjava filter za sekcije u tabu 'Vozovi'."""
        for i in reversed(range(self.sekcije_filter_layout.count())):
            item = self.sekcije_filter_layout.itemAt(i)
            if item and item.widget() != self.all_sekcije_cb:
                widget = item.widget()
                if widget:
                    widget.deleteLater()

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT sekcija FROM vozovi WHERE sekcija IS NOT NULL ORDER BY sekcija")
        sekcije = [str(row[0]) for row in cursor.fetchall() if row[0] is not None]
        conn.close()

        for s in sekcije:
            cb = QCheckBox(s)
            cb.setChecked(True)
            cb.stateChanged.connect(
                lambda state, checkbox=cb: self.on_individual_checkbox_changed(
                    state, checkbox, self.all_sekcije_cb, lambda: self.ucitaj_podatke(sort_column=None, sort_order=None)
                )
            )
            self.sekcije_filter_layout.addWidget(cb)

    def populate_serije_filter(self):
        """Popunjava filter za serije u tabu 'Vozovi'."""
        if hasattr(self, 'serije_filter_layout'):
            while self.serije_filter_layout.count() > 1:
                item = self.serije_filter_layout.takeAt(1)
                if item and item.widget():
                    item.widget().deleteLater()

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT DISTINCT serija_vozila FROM vozovi WHERE serija_vozila IS NOT NULL ORDER BY serija_vozila")
        serije = [str(row[0]) for row in cursor.fetchall() if row[0]]
        conn.close()

        for s in serije:
            cb = QCheckBox(s)
            cb.setChecked(True)
            cb.stateChanged.connect(
                lambda state, checkbox=cb: self.on_individual_checkbox_changed(
                    state, checkbox, self.all_serije_cb, lambda: self.ucitaj_podatke(sort_column=None, sort_order=None)
                )
            )
            self.serije_filter_layout.addWidget(cb)

    def populate_nazivi_filter(self):
        """Popunjava filter za nazive turnusa u tabu 'Turnusi'."""
        for i in reversed(range(self.naziv_filter_layout.count())):
            item = self.naziv_filter_layout.itemAt(i)
            if item and item.widget() != self.all_nazivi_cb:
                widget = item.widget()
                if widget:
                    widget.deleteLater()

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT naziv FROM turnusi WHERE naziv IS NOT NULL ORDER BY naziv")
        nazivi = [str(row[0]) for row in cursor.fetchall() if row[0] is not None]
        conn.close()

        for n in nazivi:
            cb = QCheckBox(n)
            cb.setChecked(True)
            cb.stateChanged.connect(
                lambda state, checkbox=cb: self.on_individual_checkbox_changed(
                    state, checkbox, self.all_nazivi_cb, lambda: self.ucitaj_turnuse(sort_column=None, sort_order=None)
                )
            )
            self.naziv_filter_layout.addWidget(cb)

    def populate_sekcije_turnusi_filter(self):
        """Popunjava filter za sekcije u tabu 'Turnusi'."""
        for i in reversed(range(self.sekcije_turnusi_filter_layout.count())):
            item = self.sekcije_turnusi_filter_layout.itemAt(i)
            if item and item.widget() != self.all_sekcije_turnusi_cb:
                widget = item.widget()
                if widget:
                    widget.deleteLater()

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT sekcija FROM turnusi WHERE sekcija IS NOT NULL ORDER BY sekcija")
        sekcije = [str(row[0]) for row in cursor.fetchall() if row[0] is not None]
        conn.close()

        for s in sekcije:
            cb = QCheckBox(s)
            cb.setChecked(True)
            cb.stateChanged.connect(
                lambda state, checkbox=cb: self.on_individual_checkbox_changed(
                    state, checkbox, self.all_sekcije_turnusi_cb,
                    lambda: self.ucitaj_turnuse(sort_column=None, sort_order=None)
                )
            )
            self.sekcije_turnusi_filter_layout.addWidget(cb)

    def populate_serije_vv_filter(self):
        """Popunjava filter za serije VV u tabu 'Turnusi'."""
        if hasattr(self, 'serije_vv_filter_layout'):
            while self.serije_vv_filter_layout.count() > 1:
                item = self.serije_vv_filter_layout.takeAt(1)
                if item and item.widget():
                    item.widget().deleteLater()

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT serija_vv FROM turnusi WHERE serija_vv IS NOT NULL ORDER BY serija_vv")
        serije = [str(row[0]) for row in cursor.fetchall() if row[0]]
        conn.close()

        for s in serije:
            cb = QCheckBox(s)
            cb.setChecked(True)
            cb.stateChanged.connect(
                lambda state, checkbox=cb: self.on_individual_checkbox_changed(
                    state, checkbox, self.all_serije_vv_cb,
                    lambda: self.ucitaj_turnuse(sort_column=None, sort_order=None)
                )
            )
            self.serije_vv_filter_layout.addWidget(cb)

    def populate_grafik_filter(self):
        """Popunjava sve filtere u tabu 'Grafik'."""
        # --- Popuni filter po turnusima ---
        if hasattr(self, 'grafik_filter_layout'):
            while self.grafik_filter_layout.count() > 1:
                item = self.grafik_filter_layout.takeAt(1)
                if item and item.widget():
                    item.widget().deleteLater()
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT id, naziv, sekcija, serija_vv FROM turnusi ORDER BY naziv")
            turnusi = cursor.fetchall()
            conn.close()
            for turnus in turnusi:
                cb = QCheckBox(f"{turnus[1]}")
                cb.setChecked(True)
                cb.turnus_id = turnus[0]
                cb.sekcija = turnus[2] or ""
                cb.serija_vv = turnus[3] or ""
                cb.stateChanged.connect(
                    lambda state, checkbox=cb: self.on_individual_checkbox_changed(
                        state, checkbox, self.all_turnusi_cb, self.crtaj_grafik
                    )
                )
                self.grafik_filter_layout.addWidget(cb)

        # --- Popuni filter po sekcijama ---
        if hasattr(self, 'sekcije_grafik_layout'):
            while self.sekcije_grafik_layout.count() > 1:
                item = self.sekcije_grafik_layout.takeAt(1)
                if item and item.widget():
                    item.widget().deleteLater()
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT sekcija FROM turnusi WHERE sekcija IS NOT NULL ORDER BY sekcija")
            sekcije = [row[0] for row in cursor.fetchall() if row[0]]
            conn.close()
            for s in sekcije:
                cb = QCheckBox(s)
                cb.setChecked(True)
                cb.stateChanged.connect(
                    lambda state, checkbox=cb: self.on_individual_checkbox_changed(
                        state, checkbox, self.all_sekcije_grafik_cb, self.filter_turnuse_po_sekciji
                    )
                )
                self.sekcije_grafik_layout.addWidget(cb)

        # --- Popuni filter po seriji VV ---
        if hasattr(self, 'serije_vv_grafik_layout'):
            while self.serije_vv_grafik_layout.count() > 1:
                item = self.serije_vv_grafik_layout.takeAt(1)
                if item and item.widget():
                    item.widget().deleteLater()
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT serija_vv FROM turnusi WHERE serija_vv IS NOT NULL ORDER BY serija_vv")
            serije_vv = [row[0] for row in cursor.fetchall() if row[0]]
            conn.close()
            for s in serije_vv:
                cb = QCheckBox(s)
                cb.setChecked(True)
                cb.stateChanged.connect(
                    lambda state, checkbox=cb: self.on_individual_checkbox_changed(
                        state, checkbox, self.all_serije_vv_grafik_cb, self.filter_turnuse_po_seriji_vv
                    )
                )
                self.serije_vv_grafik_layout.addWidget(cb)

    def handle_vozovi_header_click(self, logical_index):
        """Rukuje klikom na zaglavlje kolone u tabeli vozova."""
        # Dobij prethodno zapamćene informacije o sortiranju za vozove
        last_sorted_section = self.vozi_sort_info['column']
        last_order = self.vozi_sort_info['order']

        # Ako je kliknuta ista kolona, obrni smer, inače koristi ASCENDING
        if last_sorted_section == logical_index:
            # Istа kolona - promeni smer
            new_order = Qt.SortOrder.DescendingOrder if last_order == Qt.SortOrder.AscendingOrder else Qt.SortOrder.AscendingOrder
        else:
            # Druga kolona - default je Ascending
            new_order = Qt.SortOrder.AscendingOrder

        # Ažuriraj zapamćene informacije
        self.vozi_sort_info['column'] = logical_index
        self.vozi_sort_info['order'] = new_order

        # Pozovi ucitaj_podatke sa informacijama o sortiranju
        self.ucitaj_podatke(sort_column=logical_index, sort_order=new_order)

    def ucitaj_podatke(self, sort_column=None, sort_order=None):
        """Učitava podatke o vozovima u tabelu, opciono sortirane."""
        if not hasattr(self, 'tabela') or self.tabela is None:
            return
        self.tabela.setRowCount(0)
        if (not hasattr(self, 'voz_filter_layout') or self.voz_filter_layout is None or
                not hasattr(self, 'sekcije_filter_layout') or self.sekcije_filter_layout is None):
            return

        selektovani_vozovi = []
        try:
            for i in range(1, self.voz_filter_layout.count()):
                widget = self.voz_filter_layout.itemAt(i).widget()
                if isinstance(widget, QCheckBox) and widget.isChecked():
                    selektovani_vozovi.append(widget.text())
        except RuntimeError:
            return

        selektovane_sekcije = []
        try:
            for i in range(1, self.sekcije_filter_layout.count()):
                widget = self.sekcije_filter_layout.itemAt(i).widget()
                if isinstance(widget, QCheckBox) and widget.isChecked():
                    selektovane_sekcije.append(widget.text())
        except RuntimeError:
            return

        # Selektovane serije
        selektovane_serije = []
        try:
            for i in range(1, self.serije_filter_layout.count()):
                widget = self.serije_filter_layout.itemAt(i).widget()
                if isinstance(widget, QCheckBox) and widget.isChecked():
                    selektovane_serije.append(widget.text())
        except RuntimeError:
            return

        if not self.all_vozovi_cb.isChecked() and not selektovani_vozovi:
            return
        if not self.all_sekcije_cb.isChecked() and not selektovane_sekcije:
            return
        if not self.all_serije_cb.isChecked() and not selektovane_serije:
            return

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Pripremi ORDER BY deo SQL upita
        order_by_clause = ""
        if sort_column is not None and sort_order is not None:
            # Mapiraj logički indeks kolone na naziv kolone u bazi
            column_map = {
                0: "broj_voza",
                1: "pocetna_stanica",
                2: "krajnja_stanica",
                3: "sat_polaska, minut_polaska",  # Polazak kao kombinacija
                4: "sat_dolaska, minut_dolaska",  # Dolazak kao kombinacija
                5: "serija_vozila",
                6: "status",
                7: "sekcija"
                # Kolone 8 (Uredi) i 9 (Obriši) nisu za sortiranje
            }
            db_column = column_map.get(sort_column)
            if db_column:
                order_direction = "ASC" if sort_order == Qt.SortOrder.AscendingOrder else "DESC"
                order_by_clause = f" ORDER BY {db_column} {order_direction}"

        # Ako nije zadato sortiranje, koristi defaultno sortiranje koje je zapamćeno
        if not order_by_clause:
            default_col = self.vozi_sort_info['column']
            default_order = self.vozi_sort_info['order']
            column_map = {
                0: "broj_voza",
                1: "pocetna_stanica",
                2: "krajnja_stanica",
                3: "sat_polaska, minut_polaska",
                4: "sat_dolaska, minut_dolaska",
                5: "serija_vozila",
                6: "status",
                7: "sekcija"
            }
            db_column = column_map.get(default_col, "broj_voza")
            order_direction = "ASC" if default_order == Qt.SortOrder.AscendingOrder else "DESC"
            order_by_clause = f" ORDER BY {db_column} {order_direction}"

        # Izvrši upit sa ORDER BY
        sql_query = f"SELECT * FROM vozovi{order_by_clause}"
        cursor.execute(sql_query)
        svi_podaci = cursor.fetchall()
        conn.close()

        for red in svi_podaci:
            if len(red) < 10:
                continue
            broj = str(red[0])
            sekcija_val = str(red[8]) if red[8] is not None else ""
            serija_val = str(red[9]) if red[9] is not None else ""
            status_val = str(red[7]) if red[7] is not None else "R"

            voz_odabran = self.all_vozovi_cb.isChecked() or (broj in selektovani_vozovi)
            sekcija_odabrana = self.all_sekcije_cb.isChecked() or (not selektovane_sekcije) or (
                        sekcija_val in selektovane_sekcije)
            serija_odabrana = self.all_serije_cb.isChecked() or (not selektovane_serije) or (
                        serija_val in selektovane_serije)

            if voz_odabran and sekcija_odabrana and serija_odabrana:
                row_position = self.tabela.rowCount()
                self.tabela.insertRow(row_position)

                sat_p = red[3] if red[3] is not None else 0
                min_p = red[4] if red[4] is not None else 0
                sat_d = red[5] if red[5] is not None else 0
                min_d = red[6] if red[6] is not None else 0
                podaci = [
                    broj, red[1] or "", red[2] or "",
                    f"{sat_p:02}:{min_p:02}", f"{sat_d:02}:{min_d:02}",
                    serija_val, status_val, sekcija_val
                ]
                for col, vrednost in enumerate(podaci):
                    item = QTableWidgetItem(str(vrednost))
                    item.setFlags(item.flags() ^ Qt.ItemFlag.ItemIsEditable)
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    self.tabela.setItem(row_position, col, item)

                btn_uredi = QPushButton("Uredi")
                btn_uredi.clicked.connect(lambda _, r=red: self.uredi_voz(r))
                self.tabela.setCellWidget(row_position, 8, btn_uredi)
                btn_obrisi = QPushButton("Obriši")
                btn_obrisi.clicked.connect(lambda _, b=broj: self.obrisi_voz(b))
                self.tabela.setCellWidget(row_position, 9, btn_obrisi)

        # Uvek postavi indikator sortiranja na zaglavlju na osnovu trenutno aktivnog sortiranja
        # Koristi informacije iz self.vozi_sort_info ako nisu eksplicitno prosleđene
        if sort_column is not None and sort_order is not None:
            self.tabela.horizontalHeader().setSortIndicator(sort_column, sort_order)
        else:
            col = self.vozi_sort_info['column']
            order = self.vozi_sort_info['order']
            self.tabela.horizontalHeader().setSortIndicator(col, order)

    def handle_turnusi_header_click(self, logical_index):
        """Rukuje klikom na zaglavlje kolone u tabeli turnusa."""
        # Dobij prethodno zapamćene informacije o sortiranju za turnuse
        last_sorted_section = self.turnusi_sort_info['column']
        last_order = self.turnusi_sort_info['order']

        # Ako je kliknuta ista kolona, obrni smer, inače koristi ASCENDING
        if last_sorted_section == logical_index:
            # Istа kolona - promeni smer
            new_order = Qt.SortOrder.DescendingOrder if last_order == Qt.SortOrder.AscendingOrder else Qt.SortOrder.AscendingOrder
        else:
            # Druga kolona - default je Ascending
            new_order = Qt.SortOrder.AscendingOrder

        # Ažuriraj zapamćene informacije
        self.turnusi_sort_info['column'] = logical_index
        self.turnusi_sort_info['order'] = new_order

        # Pozovi ucitaj_turnuse sa informacijama o sortiranju
        self.ucitaj_turnuse(sort_column=logical_index, sort_order=new_order)

    def ucitaj_turnuse(self, sort_column=None, sort_order=None):
        """Učitava podatke o turnusima u tabelu, opciono sortirane."""
        if not hasattr(self, 'tabela_turnusa') or self.tabela_turnusa is None:
            return
        self.tabela_turnusa.setRowCount(0)
        if (not hasattr(self, 'naziv_filter_layout') or self.naziv_filter_layout is None or
                not hasattr(self, 'sekcije_turnusi_filter_layout') or self.sekcije_turnusi_filter_layout is None or
                not hasattr(self, 'serije_vv_filter_layout') or self.serije_vv_filter_layout is None):
            return

        selektovani_nazivi = []
        try:
            for i in range(1, self.naziv_filter_layout.count()):
                widget = self.naziv_filter_layout.itemAt(i).widget()
                if isinstance(widget, QCheckBox) and widget.isChecked():
                    selektovani_nazivi.append(widget.text())
        except RuntimeError:
            return

        selektovane_sekcije = []
        try:
            for i in range(1, self.sekcije_turnusi_filter_layout.count()):
                widget = self.sekcije_turnusi_filter_layout.itemAt(i).widget()
                if isinstance(widget, QCheckBox) and widget.isChecked():
                    selektovane_sekcije.append(widget.text())
        except RuntimeError:
            return

        selektovane_serije_vv = []
        try:
            for i in range(1, self.serije_vv_filter_layout.count()):
                widget = self.serije_vv_filter_layout.itemAt(i).widget()
                if isinstance(widget, QCheckBox) and widget.isChecked():
                    selektovane_serije_vv.append(widget.text())
        except RuntimeError:
            return

        if not self.all_nazivi_cb.isChecked() and not selektovani_nazivi:
            return
        if not self.all_sekcije_turnusi_cb.isChecked() and not selektovane_sekcije:
            return
        if not self.all_serije_vv_cb.isChecked() and not selektovane_serije_vv:
            return

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Pripremi ORDER BY deo SQL upita
        order_by_clause = ""
        if sort_column is not None and sort_order is not None:
            # Mapiraj logički indeks kolone na naziv kolone u bazi
            column_map = {
                0: "naziv",
                1: "serija_vv",
                2: "vozovi_placeholder",  # Ova kolona je složena, možda nije idealna za sortiranje preko SQL
                3: "sekcija"
                # Kolona 4 (Akcije) nije za sortiranje
            }
            db_column = column_map.get(sort_column)
            if db_column and db_column != "vozovi_placeholder":  # Za sada preskoči sortiranje po vozovima
                order_direction = "ASC" if sort_order == Qt.SortOrder.AscendingOrder else "DESC"
                order_by_clause = f" ORDER BY {db_column} {order_direction}"

        # Ako nije zadato sortiranje, koristi defaultno sortiranje koje je zapamćeno
        if not order_by_clause:
            default_col = self.turnusi_sort_info['column']
            default_order = self.turnusi_sort_info['order']
            column_map = {
                0: "naziv",
                1: "serija_vv",
                3: "sekcija"
            }
            db_column = column_map.get(default_col, "naziv")
            order_direction = "ASC" if default_order == Qt.SortOrder.AscendingOrder else "DESC"
            order_by_clause = f" ORDER BY {db_column} {order_direction}"

        # Izvrši upit sa ORDER BY
        sql_query = f"SELECT id, naziv, serija_vv, sekcija FROM turnusi{order_by_clause}"
        cursor.execute(sql_query)
        turnusi = cursor.fetchall()
        conn.close()

        for turnus in turnusi:
            naziv = str(turnus[1])
            serija_vv_val = str(turnus[2]) if turnus[2] else ""
            sekcija_val = str(turnus[3]) if turnus[3] else ""

            naziv_odabran = self.all_nazivi_cb.isChecked() or (naziv in selektovani_nazivi)
            sekcija_odabrana = self.all_sekcije_turnusi_cb.isChecked() or (not selektovane_sekcije) or (
                        sekcija_val in selektovane_sekcije)
            serija_vv_odabrana = self.all_serije_vv_cb.isChecked() or (not selektovane_serije_vv) or (
                        serija_vv_val in selektovane_serije_vv)

            if naziv_odabran and sekcija_odabrana and serija_vv_odabrana:
                conn_inner = sqlite3.connect(DB_PATH)
                cursor_inner = conn_inner.cursor()
                cursor_inner.execute("""SELECT v.broj_voza FROM turnus_vozovi tv JOIN vozovi v ON tv.broj_voza = v.broj_voza
                                        WHERE tv.turnus_id = ? ORDER BY tv.redosled""", (turnus[0],))
                vozovi_str = ", ".join([v[0] for v in cursor_inner.fetchall()])
                conn_inner.close()

                r = self.tabela_turnusa.rowCount()
                self.tabela_turnusa.insertRow(r)
                self.tabela_turnusa.setItem(r, 0, QTableWidgetItem(naziv))
                self.tabela_turnusa.setItem(r, 1, QTableWidgetItem(serija_vv_val))
                self.tabela_turnusa.setItem(r, 2, QTableWidgetItem(vozovi_str))
                self.tabela_turnusa.setItem(r, 3, QTableWidgetItem(sekcija_val))

                akcije = QWidget()
                akcije_layout = QHBoxLayout(akcije)
                akcije_layout.setContentsMargins(0, 0, 0, 0)
                btn_u = QPushButton("Uredi")
                btn_u.clicked.connect(lambda _, t=turnus: self.uredi_turnus(t))
                btn_o = QPushButton("Obriši")
                btn_o.clicked.connect(lambda _, t=turnus: self.obrisi_turnus(t))
                btn_g = QPushButton("Grafik")
                btn_g.clicked.connect(lambda _, t=turnus: self.prikazi_grafik_turnusa(t))
                akcije_layout.addWidget(btn_u)
                akcije_layout.addWidget(btn_o)
                akcije_layout.addWidget(btn_g)
                self.tabela_turnusa.setCellWidget(r, 4, akcije)

        # Uvek postavi indikator sortiranja na zaglavlju na osnovu trenutno aktivnog sortiranja
        # Koristi informacije iz self.turnusi_sort_info ako nisu eksplicitno prosleđene
        if sort_column is not None and sort_order is not None and column_map.get(sort_column) != "vozovi_placeholder":
            self.tabela_turnusa.horizontalHeader().setSortIndicator(sort_column, sort_order)
        else:
            col = self.turnusi_sort_info['column']
            order = self.turnusi_sort_info['order']
            self.tabela_turnusa.horizontalHeader().setSortIndicator(col, order)

    # --- OPERACIJE SA VOZOVIMA ---

    def uredi_voz(self, podaci):
        """Postavlja podatke vozova u formu za uređivanje."""
        self.broj_voza_input.setText(str(podaci[0]))
        self.pocetna_input.setText(str(podaci[1]))
        self.krajnja_input.setText(str(podaci[2]))
        self.sat_p_input.setText(str(podaci[3]))
        self.minut_p_input.setText(str(podaci[4]))
        self.sat_d_input.setText(str(podaci[5]))
        self.minut_d_input.setText(str(podaci[6]))
        self.serija_input.setText(str(podaci[9] or ""))
        self.status_input.setText(str(podaci[7]))
        self.sekcija_input.setText(str(podaci[8] or ""))
        self.trenutni_broj_za_izmenu = str(podaci[0])

        self.btn_dodaj.setVisible(False)
        self.btn_azuriraj.setVisible(True)
        self.btn_odustani.setVisible(True)
        print(f"REŽIM IZMENE: Uređujem voz {podaci[0]}")

    def azuriraj_voz(self):
        """Pokreće proces ažuriranja vozova."""
        self.dodaj_voz()

    def odustani_od_uredjivanja(self):
        """Odustaje od uređivanja vozova i vraća formu u početno stanje."""
        self.ocisti_formu()
        self.btn_dodaj.setVisible(True)
        self.btn_azuriraj.setVisible(False)
        self.btn_odustani.setVisible(False)
        self.trenutni_broj_za_izmenu = None

    def dodaj_voz(self):
        """Dodaje novi voz ili ažurira postojeći."""
        try:
            broj = self.broj_voza_input.text().strip()
            pocetna = self.pocetna_input.text().strip()
            krajnja = self.krajnja_input.text().strip()
            sat_p = self.sat_p_input.text().strip()
            min_p = self.minut_p_input.text().strip()
            sat_d = self.sat_d_input.text().strip()
            min_d = self.minut_d_input.text().strip()
            serija = self.serija_input.text().strip() or None
            status = (self.status_input.text().strip() or 'R').upper()
            sekcija = self.sekcija_input.text().strip()

            obavezna_polja = [
                ("Broj voza", broj), ("Početna stanica", pocetna), ("Krajnja stanica", krajnja),
                ("Sat polaska", sat_p), ("Minut polaska", min_p),
                ("Sat dolaska", sat_d), ("Minut dolaska", min_d),
                ("Sekcija", sekcija),
            ]

            nedostajuci = []
            for naziv, vrednost in obavezna_polja:
                if not vrednost:
                    nedostajuci.append(naziv)
            if nedostajuci:
                QMessageBox.critical(self, "Greška u unosu",
                                     f"Neophodno je popuniti sledeća polja:\n- " + "\n- ".join(nedostajuci))
                return

            if not broj.isalnum() or len(broj) < 3 or len(broj) > 6:
                raise ValueError("Broj voza mora biti alfanumerički (3-6 karaktera).")
            if not (2 <= len(pocetna) <= 3) or not pocetna.isalpha():
                raise ValueError("Početna stanica: 2–3 slova.")
            if not (2 <= len(krajnja) <= 3) or not krajnja.isalpha():
                raise ValueError("Krajnja stanica: 2–3 slova.")
            if not sat_p.isdigit() or not (0 <= int(sat_p) <= 23):
                raise ValueError("Sat polaska mora biti broj između 0 i 23.")
            if not min_p.isdigit() or not (0 <= int(min_p) <= 59):
                raise ValueError("Minut polaska mora biti broj između 0 i 59.")
            if not sat_d.isdigit() or not (0 <= int(sat_d) <= 23):
                raise ValueError("Sat dolaska mora biti broj između 0 i 23.")
            if not min_d.isdigit() or not (0 <= int(min_d) <= 59):
                raise ValueError("Minut dolaska mora biti broj između 0 i 59.")

            sat_p = int(sat_p);
            min_p = int(min_p);
            sat_d = int(sat_d);
            min_d = int(min_d)

            conn = None
            try:
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                if self.trenutni_broj_za_izmenu is not None:
                    cursor.execute('''
                        UPDATE vozovi SET 
                            broj_voza = ?, pocetna_stanica = ?, krajnja_stanica = ?,
                            sat_polaska = ?, minut_polaska = ?, sat_dolaska = ?, minut_dolaska = ?,
                            serija_vozila = ?, status = ?, sekcija = ?
                        WHERE broj_voza = ?
                    ''', (broj, pocetna, krajnja, sat_p, min_p, sat_d, min_d, serija, status, sekcija,
                          self.trenutni_broj_za_izmenu))
                    poruka = f"Voz {broj} uspešno ažuriran!"
                else:
                    try:
                        cursor.execute('''
                            INSERT INTO vozovi (broj_voza, pocetna_stanica, krajnja_stanica,
                                sat_polaska, minut_polaska, sat_dolaska, minut_dolaska,
                                serija_vozila, status, sekcija)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (broj, pocetna, krajnja, sat_p, min_p, sat_d, min_d, serija, status, sekcija))
                        poruka = f"Voz {broj} uspešno dodat!"
                    except sqlite3.IntegrityError:
                        QMessageBox.critical(self, "Greška", f"Voz broj {broj} već postoji!")
                        return
                conn.commit()
            finally:
                if conn:
                    conn.close()

            # OSVEŽI SVE FILTERE I TABELU
            self.populate_filters_and_load_data()
            QMessageBox.information(self, "Uspeh", poruka)
            self.ocisti_formu()

            self.btn_dodaj.setVisible(True)
            self.btn_azuriraj.setVisible(False)
            self.btn_odustani.setVisible(False)
            self.trenutni_broj_za_izmenu = None

        except ValueError as e:
            QMessageBox.critical(self, "Greška u unosu", str(e))
        except Exception as e:
            QMessageBox.critical(self, "Greška", f"Greška pri čuvanju: {e}")

    def obrisi_voz(self, broj_voza):
        """Briše voz iz baze."""
        potvrda = QMessageBox.question(self, "Potvrda", f"Obriši voz {broj_voza}?")
        if potvrda == QMessageBox.StandardButton.Yes:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM vozovi WHERE broj_voza = ?", (broj_voza,))
            conn.commit()
            conn.close()

            # OSVEŽI SVE FILTERE I TABELU
            self.populate_filters_and_load_data()
            self.ocisti_formu()
            QMessageBox.information(self, "Obrađeno", f"Voz {broj_voza} obrisan.")

    def ocisti_formu(self):
        """Čisti sva input polja u formi za vozove."""
        self.broj_voza_input.clear()
        self.pocetna_input.clear()
        self.krajnja_input.clear()
        self.sat_p_input.clear()
        self.minut_p_input.clear()
        self.sat_d_input.clear()
        self.minut_d_input.clear()
        self.serija_input.clear()
        self.status_input.clear()
        self.sekcija_input.clear()

    # --- OPERACIJE SA TURNUSIMA ---
    def proveri_turnus(self):
        """Proverava ispravnost unetih podataka za turnus."""
        self.status_label.setText("")
        self.status_label.setStyleSheet("padding: 10px; background-color: #f0f0f0; border-radius: 5px;")

        naziv = self.naziv_turnusa_input.text().strip()
        serija_vv = self.serija_vv_input.text().strip()
        vozovi_text = self.vozovi_input.text().strip()
        sekcija = self.sekcija_voza_input.text().strip()

        # ✅ Provera da li su sva polja prazna
        if not any([naziv, serija_vv, vozovi_text, sekcija]):
            self.btn_proveri.setText("Sačuvaj ažuriran turnus")
            try:
                self.btn_proveri.clicked.disconnect()
            except TypeError:
                pass
            self.btn_odustani_turnus.setVisible(True)
            self.status_label.setText(
                "Polja su prazna. Kliknite 'Odustani od uređivanja' za izlaz iz režima uređivanja.")
            self.status_label.setStyleSheet("padding: 10px; background-color: #ffeb99; border-radius: 5px;")
            return

        obavezna_polja = [
            ("Naziv turnusa", naziv),
            ("Vozovi u turnusu", vozovi_text),
            ("Sekcija za vuču vozova", sekcija),
            ("Serija VV", serija_vv)
        ]

        nedostajuci = []
        for naziv_p, vrednost in obavezna_polja:
            if not vrednost:
                nedostajuci.append(naziv_p)
        if nedostajuci:
            poruka = "Neophodno je popuniti sledeća polja:\n- " + "\n- ".join(nedostajuci)
            self.status_label.setText(poruka)
            self.status_label.setStyleSheet("padding: 10px; background-color: #ffcccc; border-radius: 5px;")
            self.btn_odustani_turnus.setVisible(True)
            return

        vozovi = [v.strip() for v in vozovi_text.split(",") if v.strip()]
        if not vozovi:
            self.status_label.setText("Greška: Morate uneti bar jedan voz!")
            self.status_label.setStyleSheet("padding: 10px; background-color: #ffcccc; border-radius: 5px;")
            self.btn_odustani_turnus.setVisible(True)
            return

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        vozovi_info = {}
        for broj in vozovi:
            cursor.execute("""
                SELECT pocetna_stanica, krajnja_stanica, sat_polaska, minut_polaska, sat_dolaska, minut_dolaska, serija_vozila
                FROM vozovi WHERE broj_voza = ?
            """, (broj,))
            info = cursor.fetchone()
            if info:
                vozovi_info[broj] = {
                    "pocetna": info[0],
                    "krajnja": info[1],
                    "polazak": (info[2], info[3]),
                    "dolazak": (info[4], info[5]),
                    "serija_vozila": info[6] or "N/A"
                }
            else:
                self.status_label.setText(f"Greška: Voz {broj} ne postoji u bazi!")
                self.status_label.setStyleSheet("padding: 10px; background-color: #ffcccc; border-radius: 5px;")
                conn.close()
                self.btn_odustani_turnus.setVisible(True)
                return

        greske_serija = []
        for broj, info in vozovi_info.items():
            serija_vozila = info["serija_vozila"]
            if serija_vozila != serija_vv:
                greske_serija.append(
                    f"Voz {broj} pripada seriji {serija_vozila}, a turnus je za seriju {serija_vv}!"
                )
        if greske_serija:
            poruka = "Greške u serijama:\n" + "\n".join(greske_serija)
            self.status_label.setText(poruka)
            self.status_label.setStyleSheet("padding: 10px; background-color: #ffcccc; border-radius: 5px;")
            conn.close()
            self.btn_odustani_turnus.setVisible(True)
            return

        greske = []
        # ✅ PROVERA: Redosled i preklapanje vremena (susedni vožnje)
        for i in range(len(vozovi) - 1):
            broj_trenutni = vozovi[i]
            broj_sledeci = vozovi[i + 1]
            if broj_trenutni not in vozovi_info or broj_sledeci not in vozovi_info:
                continue
            voz_trenutni = vozovi_info[broj_trenutni]
            voz_sledeci = vozovi_info[broj_sledeci]

            if voz_trenutni["krajnja"] != voz_sledeci["pocetna"]:
                greske.append(
                    f"Voz {broj_trenutni} i {broj_sledeci}: Stanica {voz_trenutni['krajnja']} ≠ {voz_sledeci['pocetna']}")

            # Proveri vreme - konvertuj u minute od ponoći za trenutni dan
            dolazak_trenutni_m = voz_trenutni["dolazak"][0] * 60 + voz_trenutni["dolazak"][1]
            polazak_sledeci_m = voz_sledeci["polazak"][0] * 60 + voz_sledeci["polazak"][1]

            # Provera da li je trenutni voz prelazni (dolazak < polazak)
            sat_d_trenutni, min_d_trenutni = voz_trenutni["dolazak"]
            sat_p_trenutni, min_p_trenutni = voz_trenutni["polazak"]
            prelazni_trenutni = (sat_d_trenutni < sat_p_trenutni) or (
                        sat_d_trenutni == sat_p_trenutni and min_d_trenutni < min_p_trenutni)

            # Konverzija dolaska trenutnog voza u minute, uzimajući u obzir prelaz
            if prelazni_trenutni:
                # Ako je prelazni, dolazak je u narednom danu
                dolazak_trenutni_m_corr = dolazak_trenutni_m + 24 * 60
            else:
                dolazak_trenutni_m_corr = dolazak_trenutni_m

            # Provera preklapanja: dolazak_trenutni (korigovan) >= polazak_sledeci
            if dolazak_trenutni_m_corr >= polazak_sledeci_m:
                greske.append(
                    f"Voz {broj_trenutni} i {broj_sledeci}: Dolazak {voz_trenutni['dolazak'][0]:02d}:{voz_trenutni['dolazak'][1]:02d} ≥ Polazak {voz_sledeci['polazak'][0]:02d}:{voz_sledeci['polazak'][1]:02d} (preklapanje vremena u turnusu!)")

        # ✅ PROVERA: Prelazni voz na kraju niza (SPECIFIČNA PROVERA)
        if not greske and len(vozovi) > 1:
            # Ako nema grešaka do sada i ima više od jednog voza, proveri specijalni slučaj
            poslednji_voz_broj = vozovi[-1]
            prvi_voz_broj = vozovi[0]

            if poslednji_voz_broj in vozovi_info and prvi_voz_broj in vozovi_info:
                poslednji_info = vozovi_info[poslednji_voz_broj]
                prvi_info = vozovi_info[prvi_voz_broj]

                # Proveri da li je poslednji voz prelazni
                sat_d_poslednji, min_d_poslednji = poslednji_info["dolazak"]
                sat_p_poslednji, min_p_poslednji = poslednji_info["polazak"]
                prelazni_poslednji = (sat_d_poslednji < sat_p_poslednji) or (
                            sat_d_poslednji == sat_p_poslednji and min_d_poslednji < min_p_poslednji)

                if prelazni_poslednji:
                    # --- SPECIFIČNA LOGIKA ---
                    # Ako je poslednji voz prelazni, proveri da li se njegov dolazak preklapa sa polaskom prvog voz u turnusu.
                    # Preklapanje: dolazak_poslednjeg < polazak_prvog (kada se gledaju kao vremena u 24h ciklusu).
                    # Npr: 3333 (dolazak 01:20), 4444 (polazak 01:01). 01:20 NIJE < 01:01 -> Nema preklapanja po ovoj logici.
                    # Ali ako je 3333 (dolazak 01:01), 4444 (polazak 01:20). 01:01 < 01:20 -> Preklapanje.
                    # Dakle, ako je dolazak_poslednjeg_voza < polazak_prvog_voza, onda se preklapaju.
                    # Ovo je suprotno od onoga što si tražio u poslednjem primeru.
                    # ---
                    # Ponovo pročitaj zahtev:
                    # "...da je vreme dolaska voza (3333) <= od vremena polaska voza (4444)"
                    # 3333 dolazak 01:20, 4444 polazak 01:01.
                    # 01:20 <= 01:01 -> FALSE.
                    # To znači da nema preklapanja? Ne, to znači da 3333 stigne *posle* što 4444 počne.
                    # Ako voz 3333 stigne u 01:20, a voz 4444 (koji ide odmah nakon) polazi u 01:01,
                    # to znači da se voz 4444 mora čekati dok 3333 ne stigne. To je preklapanje.
                    # Dakle, preklapanje je ako: dolazak_poslednjeg_voza >= polazak_prvog_voza.
                    # U primeru: 01:20 >= 01:01 -> TRUE. Preklapanje!
                    # U primeru: 3333 (01:01), 4444 (01:20). 01:01 >= 01:20 -> FALSE. Nema preklapanja.
                    # Ovo deluje tačno.
                    # ---
                    dolazak_poslednji_min = sat_d_poslednji * 60 + min_d_poslednji
                    polazak_prvi_min = prvi_info["polazak"][0] * 60 + prvi_info["polazak"][1]

                    if dolazak_poslednji_min >= polazak_prvi_min:
                        # Preklapanje: Dolazak poslednjeg voz >= Polazak prvog voz
                        greske.append(
                            f"Prelazni voz {poslednji_voz_broj} na kraju turnusa: Dolazak {sat_d_poslednji:02d}:{min_d_poslednji:02d} ≥ Polazak {prvi_voz_broj} {prvi_info['polazak'][0]:02d}:{prvi_info['polazak'][1]:02d} (preklapanje između poslednjeg i prvog voza u turnusu!)")

        # Ako ima grešaka (bilo iz susedne provere, bilo iz poslednji-prvi), prikaži ih
        if greske:
            poruka = "Greške u redosledu/preklapanju:\n" + "\n".join(greske)
            self.status_label.setText(poruka)
            self.status_label.setStyleSheet("padding: 10px; background-color: #ffcccc; border-radius: 5px;")
            self.btn_odustani_turnus.setVisible(True)
            conn.close()
            return

        # Ako nema grešaka → aktiviraj "Sačuvaj ažuriran turnus"
        self.status_label.setText(f"Turnus '{naziv}' je ispravan! Možete ga sačuvati.")
        self.status_label.setStyleSheet("padding: 10px; background-color: #ddffdd; border-radius: 5px;")
        self.btn_proveri.setText("Sačuvaj ažuriran turnus")
        try:
            self.btn_proveri.clicked.disconnect()
        except TypeError:
            pass
        self.btn_proveri.clicked.connect(self.sacuvaj_izmene_turnusa)
        self.btn_odustani_turnus.setVisible(True)
        conn.close()

    def sacuvaj_izmene_turnusa(self):
        """Čuva novi turnus ili ažurira postojeći."""
        naziv = self.naziv_turnusa_input.text().strip()
        serija_vv = self.serija_vv_input.text().strip()
        vozovi_text = self.vozovi_input.text().strip()
        sekcija = self.sekcija_voza_input.text().strip()

        if not naziv:
            QMessageBox.critical(self, "Greška", "Naziv turnusa je obavezan!")
            return

        vozovi = [v.strip() for v in vozovi_text.split(",") if v.strip()]
        if not vozovi:
            QMessageBox.critical(self, "Greška", "Morate uneti bar jedan voz!")
            return

        conn = None
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            if self.trenutni_turnus_za_izmenu is not None:
                cursor.execute("UPDATE turnusi SET naziv = ?, serija_vv = ?, sekcija = ? WHERE id = ?",
                               (naziv, serija_vv, sekcija, self.trenutni_turnus_za_izmenu))
                cursor.execute("DELETE FROM turnus_vozovi WHERE turnus_id = ?", (self.trenutni_turnus_za_izmenu,))
                for redosled, broj_voza in enumerate(vozovi, 1):
                    cursor.execute("""
                        INSERT INTO turnus_vozovi (turnus_id, broj_voza, redosled)
                        VALUES (?, ?, ?)
                    """, (self.trenutni_turnus_za_izmenu, broj_voza, redosled))
                poruka = f"Turnus '{naziv}' uspešno ažuriran!"
            else:
                cursor.execute("SELECT id FROM turnusi WHERE naziv = ?", (naziv,))
                if cursor.fetchone():
                    QMessageBox.critical(self, "Greška", f"Turnus '{naziv}' već postoji!")
                    return
                cursor.execute("INSERT INTO turnusi (naziv, serija_vv, sekcija) VALUES (?, ?, ?)",
                               (naziv, serija_vv, sekcija))
                cursor.execute("SELECT id FROM turnusi WHERE naziv = ?", (naziv,))
                turnus_id = cursor.fetchone()[0]
                for redosled, broj_voza in enumerate(vozovi, 1):
                    cursor.execute("""
                        INSERT INTO turnus_vozovi (turnus_id, broj_voza, redosled)
                        VALUES (?, ?, ?)
                    """, (turnus_id, broj_voza, redosled))
                poruka = f"Turnus '{naziv}' uspešno dodat!"
            conn.commit()

            # OSVEŽI SVE FILTERE I TABELU
            self.populate_filters_and_load_data()
            QMessageBox.information(self, "Uspeh", poruka)

            self.naziv_turnusa_input.clear()
            self.serija_vv_input.clear()
            self.vozovi_input.clear()
            self.sekcija_voza_input.clear()
            self.status_label.setText("")
            self.btn_proveri.setText("Proveri turnus")
            try:
                self.btn_proveri.clicked.disconnect()
            except TypeError:
                pass
            self.btn_proveri.clicked.connect(self.proveri_turnus)
            self.btn_odustani_turnus.setVisible(False)
            self.trenutni_turnus_za_izmenu = None

        except Exception as e:
            QMessageBox.critical(self, "Greška", f"Greška pri čuvanju: {e}")
        finally:
            if conn:
                conn.close()

    def odustani_od_uredjivanja_turnusa(self):
        """Odustaje od uređivanja turnusa i vraća formu u početno stanje."""
        self.naziv_turnusa_input.clear()
        self.serija_vv_input.clear()
        self.vozovi_input.clear()
        self.sekcija_voza_input.clear()
        self.status_label.setText("")

        try:
            self.btn_proveri.clicked.disconnect()
        except TypeError:
            pass

        self.btn_proveri.setText("Proveri turnus")
        self.btn_proveri.clicked.connect(self.proveri_turnus)
        self.btn_odustani_turnus.setVisible(False)
        self.trenutni_turnus_za_izmenu = None

    def uredi_turnus(self, turnus):
        """Postavlja podatke turnusa u formu za uređivanje."""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT v.broj_voza
            FROM turnus_vozovi tv
            JOIN vozovi v ON tv.broj_voza = v.broj_voza
            WHERE tv.turnus_id = ?
            ORDER BY tv.redosled
        """, (turnus[0],))
        vozovi = [v[0] for v in cursor.fetchall()]
        vozovi_str = ", ".join(vozovi)

        cursor.execute("SELECT sekcija, serija_vv FROM turnusi WHERE id = ?", (turnus[0],))
        row = cursor.fetchone()
        sekcija_val = row[0] or "" if row else ""
        serija_vv_val = row[1] or "" if row else ""
        conn.close()

        self.naziv_turnusa_input.setText(turnus[1])
        self.serija_vv_input.setText(serija_vv_val)
        self.vozovi_input.setText(vozovi_str)
        self.sekcija_voza_input.setText(sekcija_val)
        self.trenutni_turnus_za_izmenu = turnus[0]

        self.btn_proveri.setText("Proveri turnus")
        try:
            self.btn_proveri.clicked.disconnect()
        except TypeError:
            pass
        self.btn_proveri.clicked.connect(self.proveri_turnus)
        self.btn_odustani_turnus.setVisible(True)

    def obrisi_turnus(self, turnus):
        """Briše turnus iz baze."""
        potvrda = QMessageBox.question(self, "Potvrda", f"Obriši turnus '{turnus[1]}'?")
        if potvrda == QMessageBox.StandardButton.Yes:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM turnus_vozovi WHERE turnus_id = ?", (turnus[0],))
            cursor.execute("DELETE FROM turnusi WHERE id = ?", (turnus[0],))
            conn.commit()
            conn.close()
            QMessageBox.information(self, "Obrađeno", f"Turnus '{turnus[1]}' obrisan.")
            # OSVEŽI SVE FILTERE I TABELU
            self.populate_filters_and_load_data()

    # --- GRAFIČKI PRIKAZ (GRAFIK) ---

    def prikazi_grafik_turnusa(self, turnus):
        """Prikazuje grafik za određeni turnus."""
        self.tabs.setCurrentIndex(2)

        try:
            for i in range(1, self.grafik_filter_layout.count()):
                widget = self.grafik_filter_layout.itemAt(i).widget()
                if isinstance(widget, QCheckBox):
                    widget.blockSignals(True)
                    widget.setChecked(False)
                    widget.blockSignals(False)
        except Exception as e:
            print(f"Greška prilikom resetovanja filtera u grafiku: {e}")

        turnus_id_trazeni = turnus[0]
        try:
            for i in range(1, self.grafik_filter_layout.count()):
                widget = self.grafik_filter_layout.itemAt(i).widget()
                if isinstance(widget, QCheckBox):
                    if hasattr(widget, 'turnus_id') and widget.turnus_id == turnus_id_trazeni:
                        widget.blockSignals(True)
                        widget.setChecked(True)
                        widget.blockSignals(False)
                        break
        except Exception as e:
            print(f"Greška prilikom selektovanja turnusa u grafiku: {e}")

        self.crtaj_grafik()

    def filter_turnuse_po_sekciji(self):
        """Filtrira turnuse u grafiku po sekciji."""
        selektovane_sekcije = []
        for i in range(1, self.sekcije_grafik_layout.count()):
            widget = self.sekcije_grafik_layout.itemAt(i).widget()
            if isinstance(widget, QCheckBox) and widget.isChecked():
                selektovane_sekcije.append(widget.text())

        if not selektovane_sekcije:
            for i in range(1, self.grafik_filter_layout.count()):
                widget = self.grafik_filter_layout.itemAt(i).widget()
                if isinstance(widget, QCheckBox):
                    widget.blockSignals(True)
                    widget.setChecked(False)
                    widget.blockSignals(False)
            return

        for i in range(1, self.grafik_filter_layout.count()):
            widget = self.grafik_filter_layout.itemAt(i).widget()
            if isinstance(widget, QCheckBox):
                should_check = widget.sekcija in selektovane_sekcije
                widget.blockSignals(True)
                widget.setChecked(should_check)
                widget.blockSignals(False)

    def filter_turnuse_po_seriji_vv(self):
        """Filtrira turnuse u grafiku po seriji VV."""
        selektovane_serije_vv = []
        for i in range(1, self.serije_vv_grafik_layout.count()):
            widget = self.serije_vv_grafik_layout.itemAt(i).widget()
            if isinstance(widget, QCheckBox) and widget.isChecked():
                selektovane_serije_vv.append(widget.text())

        if not selektovane_serije_vv:
            for i in range(1, self.grafik_filter_layout.count()):
                widget = self.grafik_filter_layout.itemAt(i).widget()
                if isinstance(widget, QCheckBox):
                    widget.blockSignals(True)
                    widget.setChecked(False)
                    widget.blockSignals(False)
            return

        for i in range(1, self.grafik_filter_layout.count()):
            widget = self.grafik_filter_layout.itemAt(i).widget()
            if isinstance(widget, QCheckBox):
                should_check = widget.serija_vv in selektovane_serije_vv
                widget.blockSignals(True)
                widget.setChecked(should_check)
                widget.blockSignals(False)

    def crtaj_grafik(self):
        """Crtanje grafičkog prikaza turnusa."""
        self.scene.clear()

        sirina_sata = 60
        # Visina jednog reda turnusa (sve linije, tekst, razmaci)
        visina_turnusa = 120 # Povecano da bi stao i broj voza i stanica iznad
        y_pocetak = 50 # Početak crtanja turnusa ispod fiksne vremenske ose

        # --- 1. FIKSIRANA VREMENSKA OSA ([0]) na vrhu ---
        # Crtamo je samo jednom, na y=0
        self.scene.addLine(0, 0, 24 * sirina_sata, 0, QPen(Qt.GlobalColor.black, 1.2)) # y=0
        # Sada crtamo vertikalne podelice i brojeve sati
        for h in range(25):
            x = h * sirina_sata
            # Kratka vertikalna podelica: dužina ~9px (≈3mm)
            self.scene.addLine(x, 0, x, 9, QPen(Qt.GlobalColor.black, 0.8))
            # Broj sata iznad podelice
            if h < 24: # Ne crtamo broj posle poslednje podelice (24:00 npr.)
                sat_tekst = f"{h % 24:02d}"
                text = self.scene.addText(sat_tekst)
                text.setFont(QFont("Arial", 8))
                text.setPos(x - 10, -30) # Ispod glavne vremenske ose (na y=0)

        # --- 2. CRTANJE SVIH IZABRANIH TURNUSA ---
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # 2.1. Dohvati sve selektovane turnuse
        selektovani_turnusi = []
        for i in range(1, self.grafik_filter_layout.count()):
            widget = self.grafik_filter_layout.itemAt(i).widget()
            if isinstance(widget, QCheckBox) and widget.isChecked():
                if hasattr(widget, 'turnus_id'):
                    selektovani_turnusi.append(widget.turnus_id)

        if not selektovani_turnusi:
            conn.close()
            return

        # 2.2. Dohvati sve sekcije za filtriranje
        selektovane_sekcije = []
        for i in range(1, self.sekcije_grafik_layout.count()):
            widget = self.sekcije_grafik_layout.itemAt(i).widget()
            if isinstance(widget, QCheckBox) and widget.isChecked():
                selektovane_sekcije.append(widget.text())

        if not self.all_sekcije_grafik_cb.isChecked() and not selektovane_sekcije:
            conn.close()
            return

        # 2.3. Dohvati sve serije VV za filtriranje
        selektovane_serije_vv = []
        for i in range(1, self.serije_vv_grafik_layout.count()):
            widget = self.serije_vv_grafik_layout.itemAt(i).widget()
            if isinstance(widget, QCheckBox) and widget.isChecked():
                selektovane_serije_vv.append(widget.text())

        if not self.all_serije_vv_grafik_cb.isChecked() and not selektovane_serije_vv:
            conn.close()
            return

        # 2.4. Pripremi listu ID-eva selektovanih turnusa
        # (Ovaj korak je već urađen u 2.1, ali ostaje za slučaj da se doda dodatna logika kasnije)

        # 2.5. Dohvati sve vozove za selektovane turnuse, sortirane po turnusu i redosledu
        placeholders = ','.join('?' * len(selektovani_turnusi)) # ← ISPOD OVOG REDA JE BILA GREŠKA
        cursor.execute(f"""
            SELECT tv.turnus_id, tv.redosled, tv.broj_voza, 
                v.pocetna_stanica, v.krajnja_stanica,
                v.sat_polaska, v.minut_polaska, v.sat_dolaska, v.minut_dolaska, v.status, v.serija_vozila
            FROM turnus_vozovi tv
            JOIN vozovi v ON tv.broj_voza = v.broj_voza
            WHERE tv.turnus_id IN ({placeholders})
            ORDER BY tv.turnus_id, tv.redosled
        """, selektovani_turnusi)
        
        podaci = cursor.fetchall()
        conn.close()

        # 2.6. Grupiši podatke po turnusima i nacrtaj svaki turnus
        y_trenutni = y_pocetak
        trenutni_turnus_id = None
        vozovi_u_turnusu = []

        for red in podaci:
            turnus_id, redosled, broj_voza, pocetna_stanica, krajnja_stanica, \
            sat_polaska, minut_polaska, sat_dolaska, minut_dolaska, status, serija_vozila = red

            if turnus_id != trenutni_turnus_id and vozovi_u_turnusu:
                # Nacrtaj prethodni turnus
                self._crtaj_jedan_turnus(vozovi_u_turnusu, y_trenutni, sirina_sata, visina_turnusa)
                # Pripremi se za sledeći turnus
                y_trenutni += visina_turnusa
                vozovi_u_turnusu = []

            trenutni_turnus_id = turnus_id
            vozovi_u_turnusu.append({
                'broj': broj_voza,
                'pocetna': pocetna_stanica,
                'krajnja': krajnja_stanica,
                'polazak': (sat_polaska, minut_polaska),
                'dolazak': (sat_dolaska, minut_dolaska),
                'status': status,
                'serija_vozila': serija_vozila or "N/A"
            })

        # Nacrtaj poslednji turnus
        if vozovi_u_turnusu:
            self._crtaj_jedan_turnus(vozovi_u_turnusu, y_trenutni, sirina_sata, visina_turnusa)
            y_trenutni += visina_turnusa

        # --- 3. POSTAVI GRANICE SCENE ---
        max_visina = y_trenutni + 50
        self.scene.setSceneRect(0, 0, 24 * sirina_sata, max_visina)

    def _crtaj_jedan_turnus(self, vozovi, y, sirina_sata, visina_turnusa):
        """Pomoćna funkcija za crtanje jednog turnusa u grafiku."""
        if not vozovi:
            return

        # --- IZRACUNAVANJE Y KOORDINATA ZA NOVI RASPORED ---
        # Visina svakog reda unutar turnusa
        visina_reda = 20 # px (≈ 5mm)
        
        # y koordinate elemenata unutar turnusa
        gornja_linija_y = y + 30
        donja_linija_y = gornja_linija_y + 20 # Razmak ~20px ≈ 5mm
        tekst_gore_y = gornja_linija_y - 25
        tekst_dole_y = donja_linija_y + 10
        broj_vozila_x = 10
        broj_vozila_y = gornja_linija_y - 5 # Vertikalno centriran sa putem voza

        # --- CRTANJE ELEMENTA TURNUSA ---
        
        # 1. Broj vučnog vozila (1) - levo od svih linija, boldiran, centriran sa putem voza
        text_broj_vozila = self.scene.addText("1")
        font_broj_vozila = QFont()
        font_broj_vozila.setBold(True)
        text_broj_vozila.setFont(font_broj_vozila)
        # Postavi na y tako da bude centriran sa putem voza (gornja_linija_y + visina_reda/2)
        # Ako je gornja_linija_y = y + 30, a visina_reda = 20, centar je na y + 40
        # Tekst se crta od svog gornjeg levog ugla, pa moramo da podesimo y
        # Pretpostavimo da je visina teksta oko 15px
        visina_teksta_broja = text_broj_vozila.boundingRect().height()
        y_centar_puta = gornja_linija_y + visina_reda / 2
        y_tekst_broj_vozila = y_centar_puta - visina_teksta_broja / 2
        text_broj_vozila.setPos(broj_vozila_x, y_tekst_broj_vozila)

        # 2. Glavne horizontalne linije puta turnusa - ograničene na 12 sati (1440px)
        self.scene.addLine(0, gornja_linija_y, 24 * sirina_sata, gornja_linija_y, QPen(Qt.GlobalColor.black, 1.2))
        self.scene.addLine(0, donja_linija_y, 24 * sirina_sata, donja_linija_y, QPen(Qt.GlobalColor.black, 1.2))
        
        # 3. Vertikalne podelice na glavnim linijama puta - na svakih sat vremena
        # Crtamo za sat 0, 1, ..., 24 (uključujući 24 za krajnju podelu)
        for sat in range(25): # 0 do 24
            x = sat * sirina_sata
            # Kratka vertikalna podelica: dužina ~9px (≈3mm) na gornjoj liniji [3A/B] i [5A/B]
            self.scene.addLine(x, gornja_linija_y - 3, x, gornja_linija_y + 3, QPen(Qt.GlobalColor.black, 0.8))
            # Kratka vertikalna podelica: dužina ~9px (≈3mm) na donjoj liniji [3A/B] i [5A/B]
            self.scene.addLine(x, donja_linija_y - 3, x, donja_linija_y + 3, QPen(Qt.GlobalColor.black, 0.8))
            
            # Broj sata iznad gornje linije [0A/B]
            # Oznaka zavisi od toga koji je red (A ili B), ali za sada crtamo samo jedan red
            # Pretpostavimo da je ovo za red A (00-12) ili B (12-24)
            # Ako je za red A: sat_za_prikaz = sat (0-12)
            # Ako je za red B: sat_za_prikaz = sat + 12 (12-24)
            # Ova funkcija se koristi za crtanje običnog turnusa, pa crtamo 0-24
            sat_za_prikaz = sat # 0, 1, ..., 24
            sat_tekst = f"{sat_za_prikaz:02d}"
            text_sat = self.scene.addText(sat_tekst)
            font_sat = QFont("Arial", 8)
            # text_sat.setFont(font_sat) # Postavi font
            # Centriraj tekst iznad podelice
            rect_sat = text_sat.boundingRect()
            text_sat.setPos(x - rect_sat.width() / 2, -30) # Ispod glavne vremenske ose (na y=0)

        # --- STILOVI LINIJA VOZNJI ---
        pen = QPen(Qt.GlobalColor.black, 2)
        style_map = {
            'R': Qt.PenStyle.SolidLine,
            'L': Qt.PenStyle.DashLine,
            'RE': Qt.PenStyle.DotLine,
            'S': Qt.PenStyle.DashDotLine,
            'V': Qt.PenStyle.DashDotDotLine
        }

        # --- CRTANJE SVAKOG VOZA U TURNUSU ---
        for i, voz in enumerate(vozovi):
            # a) Izračunaj x koordinate za polazak i dolazak u odnosu na ceo dan (0-24)
            # Pretvori vreme u minute od ponoći (00:00)
            sat_p, min_p = voz["polazak"]
            sat_d, min_d = voz["dolazak"]
            minuti_p = sat_p * 60 + min_p
            minuti_d = sat_d * 60 + min_d

            # b) Linija vožnje - ograničena na zadati opseg (0-24 sati)
            # x koordinate u pikselima
            x_p = (minuti_p / 60.0) * sirina_sata
            x_d = (minuti_d / 60.0) * sirina_sata
            linija_y = gornja_linija_y + 10 # Linija vožnje u sredini između [3A/B] i [5A/B]

            # Postavi stil linije
            pen.setStyle(style_map.get(voz['status'], Qt.PenStyle.SolidLine))
            
            # Nacrtaj liniju vožnje (samo deo unutar opsega 0-24)
            # Provera da li linija ima presek sa opsegom 0-24 (0 - 1440 minuta)
            opseg_x_pocetak = 0
            opseg_x_kraj = 24 * sirina_sata
            if not (x_p > opseg_x_kraj or x_d < opseg_x_pocetak): # Standardna provera preseka intervala
                 # Postoji presek, crtamo deo linije koji pripada opsegu
                 clipped_x1 = max(x_p, opseg_x_pocetak)
                 clipped_x2 = min(x_d, opseg_x_kraj)
                 self.scene.addLine(clipped_x1, linija_y, clipped_x2, linija_y, pen)

            # c) Broj voza (centrirano između x_p i x_d unutar opsega, boldiran)
            if not (x_p > opseg_x_kraj or x_d < opseg_x_pocetak):
                 clipped_x1 = max(x_p, opseg_x_pocetak)
                 clipped_x2 = min(x_d, opseg_x_kraj)
                 text_broj = self.scene.addText(voz['broj'])
                 font_broj = QFont()
                 font_broj.setBold(True) # Boldiran
                 text_broj.setFont(font_broj)
                 # Podigni tekst naviše za ~3mm (≈11.34px, zaokružimo na 10px)
                 #text_broj.setPos((clipped_x1 + clipped_x2) / 2 - 20, tekst_gore_y - 10) JAAAAA
                 text_broj.setPos((clipped_x1 + clipped_x2) / 2 - 20, tekst_gore_y - 8)

            # d) Minuti (pored x_p i x_d, ali samo ako su unutar opsega)
            # Podigni tekst naviše za ~3mm (≈11.34px, zaokružimo na 10px)
            if opseg_x_pocetak <= x_p <= opseg_x_kraj:
                 text_min_p = self.scene.addText(f"{min_p:02d}") # minuti
                 #text_min_p.setPos(x_p - 10, tekst_dole_y - 10) JAAAAA
                 text_min_p.setPos(x_p - 10, tekst_dole_y - 8)
            if opseg_x_pocetak <= x_d <= opseg_x_kraj:
                 text_min_d = self.scene.addText(f"{min_d:02d}") # minuti
                 #text_min_d.setPos(x_d - 10, tekst_dole_y - 10) JAAAA
                 text_min_d.setPos(x_d - 10, tekst_dole_y - 8)

            # e) Stanice (samo za prvi i poslednji voz u turnusu, normalan font, podignut tekst)
            # Podigni tekst naviše za ~3mm (≈11.34px, zaokružimo na 10px)
            if i == 0: # Prvi voz u turnusu
                 # Proveri da li je x_p unutar opsega da bi crtali stanicu
                 if opseg_x_pocetak <= x_p <= opseg_x_kraj:
                      text_pocetna = self.scene.addText(voz['pocetna'])
                      font_stanica = QFont()
                      # font_stanica.setBold(True) # NE BOLDIRATI
                      text_pocetna.setFont(font_stanica)
                      #text_pocetna.setPos(x_p - 20, tekst_gore_y - 15 - 10) # Podignut za 10px JAAAAA
                      text_pocetna.setPos(x_p - 20, tekst_gore_y - 15 - 10) # Podignut za 10px
            if i == len(vozovi) - 1: # Poslednji voz u turnusu
                 # Proveri da li je x_d unutar opsega da bi crtali stanicu
                 if opseg_x_pocetak <= x_d <= opseg_x_kraj:
                      text_krajnja = self.scene.addText(voz['krajnja'])
                      font_stanica = QFont()
                      # font_stanica.setBold(True) # NE BOLDIRATI
                      text_krajnja.setFont(font_stanica)
                      #text_krajnja.setPos(x_d - 20, tekst_gore_y - 15 - 10) # Podignut za 10px JAAAAA
                      text_krajnja.setPos(x_d - 20, tekst_gore_y - 15 - 8) # Podignut za 10px JAAAAA

            else:
                 # Srednji vozi - stanica dolaska trenutnog = stanica polaska sledećeg
                 # crtamo između x_d trenutnog i x_p sledećeg, ako je unutar opsega
                 # Podigni tekst naviše za ~3mm (≈11.34px, zaokružimo na 10px)
                 if i < len(vozovi) - 1:
                      sledeci = vozovi[i + 1]
                      x_d_trenutni = x_d
                      x_p_sledeci = (sledeci['polazak'][0] * 60 + sledeci['polazak'][1]) / 60 * sirina_sata
                      
                      # x_sredina je tačka između dolaska trenutnog i polaska sledećeg
                      # Ali crtamo samo ako je ta tačka unutar opsega
                      x_sredina = (x_d_trenutni + x_p_sledeci) / 2
                      if opseg_x_pocetak <= x_sredina <= opseg_x_kraj:
                           text_srednja = self.scene.addText(voz['krajnja'])
                           font_stanica = QFont()
                           # font_stanica.setBold(True) # NE BOLDIRATI
                           text_srednja.setFont(font_stanica)
                           #text_srednja.setPos(x_sredina - 20, tekst_gore_y - 15 - 10) # Podignut za 10px JAAAAA
                           text_srednja.setPos(x_sredina - 20, tekst_gore_y - 15 - 8) # Podignut za 10px

    def snimi_godinu_za_grafik(self):
        """Čuva trenutno unetu godinu u atribut i fajl."""
        godina = self.godina_input.text().strip()
        self.godina_za_grafik = godina
        # Čuvanje u tekstualni fajl
        try:
            with open("data/godina_grafik.txt", "w", encoding="utf-8") as f:
                f.write(godina)
        except Exception as e:
            print(f"Greška pri čuvanju godine za grafik: {e}")

    def ucitaj_godinu_za_grafik(self):
        """Učitava prethodno sačuvanu godinu iz fajla."""
        try:
            with open("data/godina_grafik.txt", "r", encoding="utf-8") as f:
                godina = f.read().strip()
                self.godina_za_grafik = godina
                # Ako je input već inicijalizovan (nakon što se kreira UI), ažuriraj ga
                # Proveri da li atribut postoji pre nego što ga koristiš
                if hasattr(self, 'godina_input') and self.godina_input:
                    self.godina_input.setText(godina)
        except FileNotFoundError:
            # Ako fajl ne postoji, koristi prazan string ili podrazumevanu vrednost
            self.godina_za_grafik = ""
            # Isto, ažuriraj input samo ako postoji
            if hasattr(self, 'godina_input') and self.godina_input:
                self.godina_input.setText("")
        except Exception as e:
            print(f"Greška pri učitavanju godine za grafik: {e}")

    def prikazi_prosireni_turnus(self):
        """Prikazuje 'prosireni' turnus u dva reda na osnovu vremena polaska."""
        naziv_turnusa = self.naziv_prosirenog_input.text().strip()

        if not naziv_turnusa:
            QMessageBox.warning(self, "Upozorenje", "Morate uneti naziv turnusa.")
            return

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # 1. Proveri da li turnus postoji i uzmi njegov ID
        cursor.execute("SELECT id FROM turnusi WHERE naziv = ?", (naziv_turnusa,))
        turnus_result = cursor.fetchone()
        if not turnus_result:
            conn.close()
            QMessageBox.critical(self, "Greška", f"Turnus '{naziv_turnusa}' ne postoji.")
            return

        turnus_id = turnus_result[0]

        # 2. Dohvati sve vozove za taj turnus, sortirane po redosledu
        cursor.execute("""
            SELECT v.broj_voza, v.pocetna_stanica, v.krajnja_stanica,
                   v.sat_polaska, v.minut_polaska, v.sat_dolaska, v.minut_dolaska, v.status, v.serija_vozila
            FROM turnus_vozovi tv
            JOIN vozovi v ON tv.broj_voza = v.broj_voza
            WHERE tv.turnus_id = ?
            ORDER BY tv.redosled
        """, (turnus_id,))
        
        vozovi_raw = cursor.fetchall()
        conn.close()

        if not vozovi_raw:
            QMessageBox.information(self, "Informacija", f"Turnus '{naziv_turnusa}' nema vozove.")
            return

        # 3. Transformiši podatke u listu rečnika (kao u _crtaj_jedan_turnus)
        vozovi_full_info = []
        for v in vozovi_raw:
             vozovi_full_info.append({
                 "broj": v[0], "pocetna": v[1], "krajnja": v[2],
                 "polazak": (v[3], v[4]), "dolazak": (v[5], v[6]),
                 "status": v[7], "serija_vozila": v[8] or "N/A"
             })

        # 4. Podeli vozove na dva dela: pre 12:00 i od 12:00
        deo1_pre_podne = []
        deo2_posle_podne = []
        for voz in vozovi_full_info:
            sat_p = voz["polazak"][0]
            if sat_p < 12:
                deo1_pre_podne.append(voz)
            else: # sat_p >= 12
                deo2_posle_podne.append(voz)

        # 5. Pripremi scenu za crtanje (KORISTI self.scene IZ GRAFIKA)
        # Proveri da li self.scene i self.view postoje (iz create_tab_grafik)
        if not hasattr(self, 'scene') or not hasattr(self, 'view'):
             QMessageBox.critical(self, "Greška", "Scena za grafik nije inicijalizovana.")
             return

        self.scene.clear()

        # 6. Parametri za crtanje (možeš ih prilagoditi)
        sirina_sata = 60
        visina_reda = 120
        y_pocetak = 50
        razmak_izmedju_redova = 30 # Vertikalni razmak između dva reda turnusa

        # 7. Nacrtaj prvi deo (00-12 sati)
        if deo1_pre_podne:
            y_deo1 = y_pocetak
            self._crtaj_jedan_turnus_prosireni(deo1_pre_podne, y_deo1, sirina_sata, visina_reda, 0, 12)

        # 8. Nacrtaj drugi deo (12-24 sati)
        if deo2_posle_podne:
            # y koordinata za drugi deo
            # Ako postoji prvi deo, crtamo ispod njega + razmak. Ako ne, crtamo od y_pocetak
            y_deo2 = y_pocetak + (visina_reda if deo1_pre_podne else 0) + (razmak_izmedju_redova if (deo1_pre_podne and deo2_posle_podne) else 0)
            self._crtaj_jedan_turnus_prosireni(deo2_posle_podne, y_deo2, sirina_sata, visina_reda, 12, 24)

        # 9. Postavi veličinu scene (pojednostavljeno)
        max_y = y_pocetak + (visina_reda if deo1_pre_podne else 0) + (razmak_izmedju_redova if (deo1_pre_podne and deo2_posle_podne) else 0) + (visina_reda if deo2_posle_podne else 0) + 50
        self.scene.setSceneRect(0, 0, 24 * sirina_sata, max_y)

        # 10. Prebaci fokus na tab "Pregled Grafika"
        # Pretpostavljamo da je self.tabs instanca QTabWidget i da je:
        # 0 - Vozovi, 1 - Turnusi, 2 - Grafik, 3 - Stampa
        if hasattr(self, 'tabs'):
             self.tabs.setCurrentIndex(2) # Indeks taba "Grafik"

        QMessageBox.information(self, "Uspeh", f"Prošireni prikaz turnusa '{naziv_turnusa}' je generisan.")

    def _crtaj_jedan_turnus_prosireni(self, vozovi, y, sirina_sata, visina_turnusa, pocetni_sat, krajnji_sat):
        """
        Pomoćna funkcija za crtanje jednog 'reda' turnusa sa prilagođenom vremenskom osom.
        Slična _crtaj_jedan_turnus, ali sa ograničenom vremenskom osom.
        """
        if not vozovi:
            return

        # --- IZRACUNAVANJE Y KOORDINATA ZA NOVI RASPORED ---
        # Visina svakog reda unutar turnusa
        visina_reda = 20 # px (≈ 5mm)
        
        # y koordinate elemenata unutar turnusa
        # Red 1: Broj vučnog vozila (1) i nazivi stanica (normalni font)
        # Visina teksta je oko 15px, pa da bi bio centriran sa putem voza, y treba da bude oko y_puta - 7.5px
        # Prethodno: red1_y = y + 10. Sada: podesimo da bude više, npr. y + 25 - 7.5 = y + 17.5
        # A možemo i da podesimo da bude tačno na sredini između [3] i [5], što je y + 30 + 10 = y + 40
        # Ali broj vučnog vozila treba da bude levo od početka linije, dakle x < 0.
        # Pa ćemo ga postaviti na y + 30 + 10 - visina_teksta/2 = y + 40 - 7.5 = y + 32.5
        red1_y_tekst = y + 32.5 # Visina teksta broja vozila i stanica, centrirana sa putem voza
        
        # Red 2: Linije puta turnusa ([3] i [5])
        red2_gornja_linija_y = y + 30 # Linija [3] ili [5] (gornja)
        red2_donja_linija_y = red2_gornja_linija_y + visina_reda # Linija [3] ili [5] (donja)
        
        # Red 3: Linije vožnji i brojevi vozova (bold font)
        red3_linija_voznje_y = red2_gornja_linija_y + visina_reda / 2 # Linija vožnje u sredini
        red3_tekst_broj_y = red2_gornja_linija_y - 15 # Broj voza iznad linije vožnje, ali podignut za 15px umesto 25px
        
        # Red 4: Minuti
        red4_tekst_minuti_y = red2_donja_linija_y + 10 # Minuti ispod donje linije

        # --- CRTANJE ELEMENTA TURNUSA ---
        
        # 1. Broj vučnog vozila (1) - levo od svih linija, u Redu 1, centriran sa putem voza
        broj_vozila_x = -30 # Malo levo od početka scene (0)
        broj_vozila_y = red1_y_tekst - 7.5 # Centrirano sa putem voza
        text_broj_vozila = self.scene.addText("1")
        font_broj_vozila = QFont()
        font_broj_vozila.setBold(True) # Boldiran
        text_broj_vozila.setFont(font_broj_vozila)
        text_broj_vozila.setPos(broj_vozila_x, broj_vozila_y)

        # 2. Nazivi stanica - u Redu 1, iznad linija puta, normalan font, podignuti naviše za ~10px
        # Prvi voz - početna stanica
        prvi_voz = vozovi[0]
        x_p_prvi = (prvi_voz['polazak'][0] * 60 + prvi_voz['polazak'][1]) / 60 * sirina_sata
        text_pocetna = self.scene.addText(prvi_voz['pocetna'])
        font_stanica = QFont()
        # font_stanica.setBold(True) # Uklonjeno boldiranje
        text_pocetna.setFont(font_stanica)
        # Podignuto naviše za ~10px
        #text_pocetna.setPos(x_p_prvi - 20, red1_y_tekst - 7.5 - 10) # Normalan font, podignut JAAAAA
        text_pocetna.setPos(x_p_prvi - 20, red1_y_tekst - 7.5 - 8) # Normalan font, podignut

        # Poslednji voz - krajnja stanica
        poslednji_voz = vozovi[-1]
        x_d_poslednji = (poslednji_voz['dolazak'][0] * 60 + poslednji_voz['dolazak'][1]) / 60 * sirina_sata
        text_krajnja = self.scene.addText(poslednji_voz['krajnja'])
        # font_krajnja = QFont() # Ako želiš da koristiš isti font kao i za početnu
        # text_krajnja.setFont(font_krajnja)
        # text_krajnja.setPos(x_d_poslednji - 20, red1_y_tekst - 7.5 - 10) # Normalan font, podignut
        # Ili ako želiš da koristiš isti font kao i za početnu:
        text_krajnja.setFont(font_stanica) # Isti font kao i za početnu
        #text_krajnja.setPos(x_d_poslednji - 20, red1_y_tekst - 7.5 - 10) # Normalan font, podignut JAAAAA
        text_krajnja.setPos(x_d_poslednji - 20, red1_y_tekst - 7.5 - 8) # Normalan font, podignut

        # Srednji vozi - stanica dolaska trenutnog = stanica polaska sledećeg
        for i in range(len(vozovi) - 1):
            voz_trenutni = vozovi[i]
            voz_sledeci = vozovi[i + 1]
            x_d_trenutni = (voz_trenutni['dolazak'][0] * 60 + voz_trenutni['dolazak'][1]) / 60 * sirina_sata
            x_p_sledeci = (voz_sledeci['polazak'][0] * 60 + voz_sledeci['polazak'][1]) / 60 * sirina_sata
            # x_sredina je tačka između dolaska trenutnog i polaska sledećeg
            x_sredina = (x_d_trenutni + x_p_sledeci) / 2
            text_srednja = self.scene.addText(voz_trenutni['krajnja']) # Stanica dolaska trenutnog
            # text_srednja.setFont(QFont()) # Normalan font
            text_srednja.setFont(font_stanica) # Isti font kao i za početnu/krajnju
            # Podignuto naviše za ~10px
            #text_srednja.setPos(x_sredina - 20, red1_y_tekst - 7.5 - 10) # Normalan font, podignut JAAAAA
            text_srednja.setPos(x_sredina - 20, red1_y_tekst - 7.5 - 8) # Normalan font, podignut

        # 3. Glavne horizontalne linije puta turnusa - u Redu 2
        # Linija [3] ili [5] (gornja)
        self.scene.addLine(0, red2_gornja_linija_y, 24 * sirina_sata, red2_gornja_linija_y, QPen(Qt.GlobalColor.black, 1.2))
        # Linija [3] ili [5] (donja)
        self.scene.addLine(0, red2_donja_linija_y, 24 * sirina_sata, red2_donja_linija_y, QPen(Qt.GlobalColor.black, 1.2))
        
        # 4. Vertikalne podelice na linijama puta - u Redu 2
        for h in range(25): # 0 do 24
            x = h * sirina_sata
            # Kratka vertikalna podelica: dužina ~6px (≈2mm) na [3], ~6px (≈2mm) na [5]
            self.scene.addLine(x, red2_gornja_linija_y - 3, x, red2_gornja_linija_y + 3, QPen(Qt.GlobalColor.black, 0.8))
            self.scene.addLine(x, red2_donja_linija_y - 3, x, red2_donja_linija_y + 3, QPen(Qt.GlobalColor.black, 0.8))

        # 5. Stilovi linija
        pen = QPen(Qt.GlobalColor.black, 2)
        style_map = {
            'R': Qt.PenStyle.SolidLine,
            'L': Qt.PenStyle.DashLine,
            'RE': Qt.PenStyle.DotLine,
            'S': Qt.PenStyle.DashDotLine,
            'V': Qt.PenStyle.DashDotDotLine
        }

        # 6. Crtanje svakog voza u turnusu - u Redu 3 i Redu 4
        for i, voz in enumerate(vozovi):
            # a) Izračunaj x koordinate za polazak i dolazak u odnosu na ceo dan (0-24)
            x_p = (voz['polazak'][0] * 60 + voz['polazak'][1]) / 60 * sirina_sata
            x_d = (voz['dolazak'][0] * 60 + voz['dolazak'][1]) / 60 * sirina_sata

            # b) Linija vožnje - u Redu 3 (horizontalna ispod gornje linije)
            pen.setStyle(style_map.get(voz['status'], Qt.PenStyle.SolidLine))
            self.scene.addLine(x_p, red3_linija_voznje_y, x_d, red3_linija_voznje_y, pen)

            # c) Broj voza (centrirano iznad linije vožnje) - u Redu 3, boldiran, podignut naviše za ~10px
            text_broj = self.scene.addText(voz['broj'])
            font_broj = QFont()
            font_broj.setBold(True) # Boldiran
            text_broj.setFont(font_broj)
            # Podignuto naviše za ~10px
            #text_broj.setPos((x_p + x_d) / 2 - 20, red3_tekst_broj_y - 10) # Boldiran, podignut JAAAAA
            text_broj.setPos((x_p + x_d) / 2 - 20, red3_tekst_broj_y - 8) # Boldiran, podignut

            # d) Minuti (pored x_p i x_d) - u Redu 4
            text_min_p = self.scene.addText(f"{voz['polazak'][1]:02d}")
            text_min_d = self.scene.addText(f"{voz['dolazak'][1]:02d}")
            #text_min_p.setPos(x_p - 10, red4_tekst_minuti_y) JAAAA
            text_min_p.setPos(x_p - 8, red4_tekst_minuti_y)
            #text_min_d.setPos(x_d - 10, red4_tekst_minuti_y)
            text_min_d.setPos(x_d - 8, red4_tekst_minuti_y)


# --- POKRETANJE APLIKACIJE ---

if __name__ == "__main__":
    app = QApplication([])
    window = SimpleApp()
    window.show()
    app.exec()
