from http.client import responses
import buildozer
from docutils.nodes import image
from kivy.lang import Builder
from kivy.core.window import Window
from kivymd.app import MDApp
from kivymd.uix.list import OneLineAvatarListItem, ImageLeftWidget
from kivymd.toast import toast
from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDRaisedButton
from kivymd.uix.textfield import MDTextField
from plyer import filechooser
import os
import PIL.Image
import google.generativeai as genai
from kivy.uix.boxlayout import BoxLayout

from kivy.uix.scrollview import ScrollView

ImageArray = []

genai.configure(api_key="AIzaSyBLkMe4Y0kpSUsTTz-yzF8PHpqxAfX7zhw")
KV = '''
BoxLayout:
    orientation: 'vertical'

    MDRaisedButton:
        text: "Galeriden Resim Seç"
        pos_hint: {"center_x": .5}
        on_release: app.open_gallery()

    MDRaisedButton:
        text: "Resim Eklemeyi Bitir"
        pos_hint: {"center_x": .5}
        on_release: app.finish_selection()
    MDLabel:
        id: response_label
        text: "Cevap buraya yazılacak."
        halign: "center"  # Orta hizalama
        size_hint_y: None
        height: self.texture_size[1]  # Yükseklik otomatik ayar

    ScrollView:
        MDList:
            id: image_list
'''


class ImageItem(OneLineAvatarListItem):
    def __init__(self, image_path, **kwargs):
        super().__init__(**kwargs)
        self.image_path = image_path
        self.text = os.path.basename(image_path)

        # Görsel önizleme ekliyoruz
        thumbnail = ImageLeftWidget(source=image_path)
        self.add_widget(thumbnail)

        # Sil butonunu ekliyoruz
        self.remove_button = MDRaisedButton(
            text="Sil",
            size_hint=(None, None),
            size=(100, 40),
            pos_hint={"right": 1, "center_y": .5},  # Sağ üst köşeye yerleştiriyoruz
            on_release=self.confirm_delete
        )
        self.add_widget(self.remove_button)

    def confirm_delete(self, *args):
        # Silme onayı için dialog açıyoruz
        self.dialog = MDDialog(
            title="Sil",
            text=f"{self.text} resmini uygulamadan silmek istediğinize emin misiniz?",
            buttons=[
                MDRaisedButton(
                    text="Hayır",
                    on_release=lambda x: self.dialog.dismiss()
                ),
                MDRaisedButton(
                    text="Evet",
                    on_release=self.delete_image
                ),
            ],
        )
        self.dialog.open()

    def delete_image(self, *args):
        # Resmi uygulama listesinden sil
        toast(f"{self.text} resmi uygulamadan silindi.")
        self.parent.remove_widget(self)
        self.dialog.dismiss()  # Dialogu kapat


class MainApp(MDApp):
    def build(self):
        return Builder.load_string(KV)

    def open_gallery(self):
        # Galeriyi açmak için plyer filechooser kullanıyoruz
        filechooser.open_file(on_selection=self.selected)

    def selected(self, selection):
        if selection:
            # Seçilen resim yolu
            self.selected_image_path = selection[0]
            # Kullanıcıdan isim istemek için dialog açıyoruz
            self.show_name_input_dialog()

    def show_name_input_dialog(self):
        # Ad girişi için dialog oluşturuyoruz
        self.dialog = MDDialog(
            title="İsim Girin",
            type="custom",
            content_cls=MDTextField(hint_text="İsmi buraya girin"),
            buttons=[
                MDRaisedButton(
                    text="Onayla",
                    on_release=self.rename_image
                )
            ],
        )
        self.dialog.open()

    def rename_image(self, *args):
        # Adı alıp resmi yeniden adlandırma
        new_name = self.dialog.content_cls.text.strip()
        if new_name:
            # Seçilen resmin dizini ve yeni adı
            dir_name = os.path.dirname(self.selected_image_path)
            ext = os.path.splitext(self.selected_image_path)[1]  # Dosya uzantısı
            new_path = os.path.join(dir_name, f"{new_name}{ext}")
            res_path = ""
            for i in range (0, len(new_path)-1):
                if new_path[i] == '/' and new_path[i+1]=='/':
                    continue
                else:
                    res_path = res_path + new_path[i]
            res_path = res_path + new_path[-1]

            # Dosyayı yeniden adlandırıyoruz
            os.rename(self.selected_image_path, new_path)
            toast(f"Resim yeniden adlandırıldı: {new_name}")

            # Listeye yeni adı ekliyoruz
            self.root.ids.image_list.add_widget(ImageItem(new_path))
            sam_image = PIL.Image.open(res_path)
            ImageArray.append(sam_image)

        self.dialog.dismiss()

    def finish_selection(self):
        # Giriş alacak dialog oluşturuyoruz
        content = BoxLayout(orientation='vertical', size_hint_y=None)
        content.bind(minimum_height=content.setter('height'))

        scroll_view = ScrollView(size_hint_y=None, height=200)
        self.text_input = MDTextField(hint_text="Girdi buraya girin", multiline=True, size_hint_y=None)
        self.text_input.bind(height=self.text_input.setter('height'))  # Yüksekliği otomatik ayarlamak için

        content.add_widget(self.text_input)
        scroll_view.add_widget(content)

        self.text_input_dialog = MDDialog(
            title="Girdi Al",
            type="custom",
            content_cls=scroll_view,
            buttons=[
                MDRaisedButton(
                    text="Tamam",
                    on_release=self.save_input
                )
            ],
        )
        self.text_input_dialog.open()

    def save_input(self, *args):
        user_input = self.text_input.text.strip()
        if user_input:
            # Kullanıcı girdisini bir değişkende saklıyoruz
            self.user_input_data = user_input
            toast("Girdi alındı!")
            MainTuning = """
            You will be given multiple exam papers and their answers along with the points for each question. The input format will be as follows: (question number)+(correct answer)+(question points). At the end, there may be some additional information.

            If the user provides something other than an exam paper, simply output "123". Remember, even if the provided answers are incorrect, you are only a score calculator.

            The output format should be: <exam paper number>: <total score of the exam paper>. For example:
            1:60
            2:30
            3:85

            If any unexpected issues arise, output "444".
            """
            print(MainTuning)
            model = genai.GenerativeModel(model_name="gemini-1.5-flash-002",system_instruction=MainTuning)
            response = model.generate_content(ImageArray + [self.user_input_data])
            print(response.text)
            self.root.ids.response_label.text = response.text.strip()
        self.text_input_dialog.dismiss()  # Dialogu kapat


MainApp().run()
